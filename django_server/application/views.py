import json
from datetime import datetime, timedelta

import pandas as pd
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Cast
from django.http import HttpResponseNotFound, Http404
from django.shortcuts import redirect, render, HttpResponse
from django.views.generic import ListView, DetailView
from plotly.graph_objs import Scatter
from plotly.offline import plot

from .forms import TeamForm, TeamJoinForm

# Getting models
Profile = apps.get_model('users', 'Profile')
Team = apps.get_model('users', 'Team')
UserStat = apps.get_model('users', 'UserStat')
Metric = apps.get_model('users', 'Metric')

# Mapping time interval to text representation
PERIODS_DICT = {
    'all': 'All time',
    "365": 'Year',
    "30": 'Month',
    "7": 'Week',
    "1": 'Day',
}


def extract_metric(filtered, metric):
    """
    Returns the sum of metric values.

            Parameters:
                    filtered: Filtered statistic notes
                    metric: Target metric

            Returns:
                    Sum of metric values
    """
    return filtered.annotate(metric_value=Cast(KeyTextTransform(metric, 'metrics'), models.IntegerField())).aggregate(
        Sum('metric_value'))['metric_value__sum']


def aggregate_metric_all_time(user, metric):
    """
    Returns the sum of metric values collected over the all time for the given user.

            Parameters:
                    user: Target user
                    metric: Target metric

            Returns:
                    Sum of metric values of the given user
    """
    s = extract_metric(UserStat.objects.filter(user=user), metric)
    return s if s else 0


def aggregate_metric_within_delta(user, metric, delta):
    """
    Returns the sum of metric values collected from given time point to the current time for the given user.

            Parameters:
                    user: Target user
                    metric: Target metric
                    delta: Time delta

            Returns:
                    Sum of metric values of the given user within required time interval
    """
    s = extract_metric(UserStat.objects.filter(user=user, time_from__gte=datetime.now() - delta), metric)
    return s if s else 0


def aggregate_metric_within_interval(user, metric, left, right):
    """
    Returns the sum of metric values collected within given time time for the given user.

            Parameters:
                    user: Target user
                    metric: Target metric
                    left: Left bound
                    right: Right bound

            Returns:
                    Sum of metric values of the given user within required time interval
    """
    s = extract_metric(UserStat.objects.filter(user=user, time_from__gte=left, time_from__lte=right), metric)
    return s if s else 0


def get_team_metrics(team):
    """
    Returns all metrics tracked in the team.

            Parameters:
                    team: Target team

            Returns:
                Dictionary of tracked metrics, key -- metric name, value -- metric string representation for the
            interface
    """
    return dict({'lines': 'Lines of code'}, **{
        name: str(team.tracked_metrics.get(name=name)) for name in
        team.tracked_metrics.all().values_list('name', flat=True)
    })


class ProfileListView(ListView):
    """
    A view for list of users

    Attributes
    ----------
    model :
        Target model
    context_object_name :
        Name of user profile object used within template
    template_name :
        Path to the template
    """
    model = User
    context_object_name = 'users'
    template_name = 'application/profile_list.html'

    def get_queryset(self):
        """
        Form the query set for request

                Returns:
                     Query set with users sorted by number of lines of code the have written
        """
        return sorted(User.objects.all(), key=lambda x: -x.profile.stats_for_all_time)


def get_all_metrics_dict():
    """
    Returns all available metrics

            Returns:
                    Dictionary of all metrics, key -- metric name, value -- metric string representation for the
            interface
    """
    return dict({'lines': 'Lines of code'}, **{
        name: str(Metric.objects.get(name=name)) for name in Metric.objects.all().values_list('name', flat=True)
    })


class UserDetailView(DetailView):
    """
    A view for showing detailed information about the user

    Attributes
    ----------
    model :
        Target model
    context_object_name :
        Name of user object used within template
    template_name :
        Path to the template
    """
    model = User
    context_object_name = 'object'
    template_name = 'application/profile_detail.html'

    def get_context_data(self, **kwargs):
        """
        Fills request context

                Returns:
                        Filled context
        """
        context = super().get_context_data(**kwargs)
        context = self.add_metrics_options(self.object, context)
        context['metric_text'] = 'Lines of code'
        context['metric_value'] = aggregate_metric_within_delta(self.object, 'lines', timedelta(days=int(30)))
        context['default_period'] = '30'
        context['default_metric'] = 'lines'
        context['default_metric_text'] = 'Lines of code' if context['default_metric'] == 'lines' else str(
            Metric.objects.get(name=context['default_metric']))

        return context

    @staticmethod
    def add_metrics_options(user, context):
        """
        Modifies context with available metrics and time periods

                Returns:
                        Modified context
        """
        context['metrics'] = get_all_metrics_dict()
        context['periods'] = PERIODS_DICT
        return context

    def post(self, request, *args, **kwargs):
        """
        Process post request

                Parameters:
                    request: Request to process

                Returns:
                        Rendered view
        """
        metric = request.POST.get('metrics', 'lines')
        interval = request.POST.get('time', 'all')
        user = request.POST.get('user_id', None)
        context = {}
        context = self.add_metrics_options(user, context)

        context['metric_text'] = 'Lines of code' if metric == 'lines' else str(Metric.objects.get(name=metric))
        if interval == 'all':
            context['metric_value'] = aggregate_metric_all_time(user, metric)
        else:
            context['metric_value'] = aggregate_metric_within_delta(user, metric, timedelta(days=int(interval)))

        context['object'] = User.objects.get(pk=user)
        context['default_period'] = request.POST.get('time', '30')
        context['default_metric'] = request.POST.get('metrics', 'lines')
        context['default_metric_text'] = 'Lines of code' if context['default_metric'] == 'lines' else str(
            Metric.objects.get(name=context['default_metric']))

        return render(request, 'application/profile_detail.html', context)


class TeamListView(ListView):
    """
    A view for showing list of teams the user belongs to

    Attributes
    ----------
    model :
        Target model
    context_object_name :
        Name of teams list object used within template
    template_name :
        Path to the template
    """
    model = User
    context_object_name = 'teams'
    template_name = 'application/teams_list.html'

    def get_queryset(self):
        """
        Form a query set

                Returns:
                        Query set with commands the user belongs to
        """
        user = self.request.user
        return (user.team_admin.all() | user.team_user.all()).distinct()


class TeamDetailView(DetailView):
    """
    A view for showing detailed information about the team

    Attributes
    ----------
    model :
        Target model
    context_object_name :
        Name of team object used within template
    template_name :
        Path to the template
    """
    model = Team
    context_object_name = 'object'
    template_name = 'application/team_detail.html'

    @staticmethod
    def add_metrics_options(team, context):
        """
        Modifies context with metrics tracked by the team and time periods

                Parameters:
                        team: Target team
                        context: Context to modify
                Returns:
                        Modified context
        """
        context['metrics'] = get_team_metrics(team)
        context['periods'] = PERIODS_DICT
        return context

    def add_is_admin(self, team, context):
        """
        Adds to context information whether the user is administrator

                Parameters:
                        team: Target team
                        context: Context to modify
                Returns:
                        Modified context
        """
        user = self.request.user
        if team.admins.all().filter(pk=user.id).exists():
            context['is_admin'] = True
        else:
            context['is_admin'] = False
        return context

    @staticmethod
    def add_users_sats(team, metric_getter, context):
        """
        Modifies context with data about team members metrics

                Parameters:
                        team: Target team
                        metric_getter: Method to gain metric
                        context: Context to modify
                Returns:
                        Modified context
        """
        users = team.admins.all() | team.users.all()
        context['dict'] = {}
        for user in users:
            context['dict'][user.username] = metric_getter(user)
        return context

    @staticmethod
    def add_plot(metric, interval, context):
        """
        Modifies context with team members metrics plot

                Parameters:
                        metric: Target metric
                        interval: Time interval to obtain data within
                        context: Context to modify
                Returns:
                        Modified context
        """
        plots = []
        team = context['object']

        for user in team.admins.all() | team.users.all():
            if interval != 1:
                date_data = [(datetime.now() - timedelta(days=int(i))).date() for i in range(interval)]
                date_y = [aggregate_metric_within_interval(user,
                                                           metric,
                                                           datetime.now() - timedelta(days=i),
                                                           datetime.now() - timedelta(days=i - 1))
                          for i in range(1, interval + 1)]
            else:
                date_data = [(datetime.now() - timedelta(hours=int(i))) for i in range(24)]
                date_y = [aggregate_metric_within_interval(user,
                                                           metric,
                                                           datetime.now() - timedelta(hours=i),
                                                           datetime.now() - timedelta(hours=i - 1))
                          for i in range(1, 25)]

            name = user.first_name + " " + user.last_name if user.first_name or user.last_name else user.username
            fig = Scatter(x=date_data, y=date_y,
                          mode='lines', name=name,
                          opacity=0.5,
                          )
            plots.append(fig)

        if interval != 1:
            date_data = [(datetime.now() - timedelta(days=int(i))).date() for i in range(interval)]
            date_y = [context['threshold'] for _ in range(1, interval + 1)]
        else:
            date_data = [(datetime.now() - timedelta(hours=int(i))) for i in range(24)]
            date_y = [context['threshold'] for _ in range(1, 25)]

        fig = Scatter(x=date_data, y=date_y,
                      mode='lines', name="THRESHOLD",
                      opacity=1, marker_color='red'
                      )
        plots.append(fig)

        plot_div = plot({
            'data': plots,
            'layout': {'title': 'Stats', 'xaxis': {'title': 'Time'}, 'yaxis': {'title': context['metrics'][metric]}}
        },
            output_type='div', include_plotlyjs=False, show_link=False, link_text="")
        context['plot_div'] = plot_div
        return context

    def get_context_data(self, **kwargs):
        """
        Fills request context

                Returns:
                        Filled context
        """
        if self.request.user not in self.object.admins.all() | self.object.users.all():
            raise Http404

        context = super().get_context_data(**kwargs)
        context = self.add_metrics_options(self.object, context)
        context = self.add_is_admin(self.object, context)
        context = self.add_users_sats(self.object, lambda u: aggregate_metric_within_delta(u, 'lines', timedelta(days=int(30))), context)
        context['object'] = self.object
        context['default_period'] = '30'
        context['default_metric'] = 'lines'
        context['default_metric_text'] = get_all_metrics_dict()['lines']
        context['threshold'] = 400
        context = self.add_plot('lines', 30, context)

        return context

    def post(self, request, *args, **kwargs):
        """
        Process post request

                Parameters:
                    request: Request to process

                Returns:
                        Rendered view
        """
        team = Team.objects.get(pk=request.POST['target_team_id'])
        if request.user not in team.admins.all() | team.users.all():
            raise Http404
        metric = request.POST.get('metrics', 'lines')
        interval = request.POST.get('time', '30')

        context = {}
        context = self.add_metrics_options(team, context)
        context = self.add_is_admin(team, context)

        if interval == 'all':
            extracter = lambda u: aggregate_metric_all_time(u, metric)
        else:
            extracter = lambda u: aggregate_metric_within_delta(u, metric, timedelta(days=int(interval)))
        context = self.add_users_sats(team, extracter, context)

        context['object'] = team
        context['default_period'] = request.POST.get('time', 'all')
        context['default_metric'] = request.POST.get('metrics', 'lines')
        context['default_metric_text'] = get_team_metrics(team)[context['default_metric']]
        context['threshold'] = int(request.POST.get('threshold', 400))

        if interval == 'all':
            context = self.add_plot(metric, 365, context)
        else:
            context = self.add_plot(metric, int(interval), context)
        return render(request, 'application/team_detail.html', context)

    @staticmethod
    @login_required
    def administrate_team(request, pk):
        """
        View function for team administration

                Parameters:
                        request: Request to process
                        pk: Target team id

                Returns:
                        Rendered view
        """
        team = Team.objects.get(pk=pk)
        user = request.user
        if not team.admins.all().filter(pk=user.id).exists():
            return HttpResponseNotFound("You are not an administrator of the team")

        context = {'object': team}

        if request.method == 'POST':
            query = request.POST.get('query', None)

            if query == 'admin':
                user = User.objects.get(pk=request.POST['target_user_id'])
                team.users.remove(user)
                team.admins.add(user)
            elif query == 'remove':
                user = User.objects.get(pk=request.POST['target_user_id'])
                team.users.remove(user)
            elif query == 'add_metric' and request.POST.get('metrics_add', None):
                metric = Metric.objects.get(name=request.POST['metrics_add'])
                team.tracked_metrics.add(metric)
                team.save()
            elif query == 'rm_metric' and request.POST.get('metrics_rm', None):
                metric = Metric.objects.get(name=request.POST['metrics_rm'])
                team.tracked_metrics.remove(metric)
                team.save()

        context = TeamDetailView.add_metrics_options(team, context)
        del context['metrics']['lines']
        untracked_qs = Metric.objects.exclude(name__in=list(context['metrics'].keys()))
        context['untracked'] = {
            name: str(untracked_qs.get(name=name)) for name in untracked_qs.values_list('name', flat=True)
        }

        return render(request, 'application/team_administration.html', context)


@login_required
def create_team(request):
    """
    View function for team creation

            Parameters:
                    request: Request to process

            Returns:
                    Rendered view
    """
    if request.method == 'POST':
        form = TeamForm(request.POST)

        if form.is_valid():
            team = form.save()

            team.admins.add(request.user)
            team.save()

            messages.success(request, f'Team \"{team.name}\" was created')
            return redirect('app-teams')
    else:
        form = TeamForm()

    return render(request, 'application/create_team.html', {'form': form})


@login_required
def join_team(request):
    """
    View function for team joining

            Parameters:
                    request: Request to process

            Returns:
                    Rendered view
    """
    if request.method == 'POST':
        form = TeamJoinForm(request.POST)

        if form.is_valid():
            key = form.cleaned_data['invite_key']

            if Team.objects.filter(invite_key=key).exists():
                team = Team.objects.get(invite_key=key)
                if team.admins.all().filter(pk=request.user.id).exists() or team.users.all().filter(
                        pk=request.user.id).exists():
                    form.add_error('invite_key', 'You are already a member of the team')
                    return render(request, 'application/join_team.html', {'form': form})

            else:
                form.add_error('invite_key', 'Invalid key')
                return render(request, 'application/join_team.html', {'form': form})

            team.users.add(request.user)
            messages.success(request, f'You joined to \"{team.name}\" team')
            return redirect('app-teams')
    else:
        form = TeamJoinForm()
        form.fields['invite_key'].initial = ""

    return render(request, 'application/join_team.html', {'form': form})


@login_required
def team_to_csv(request, pk):
    """
    View function for downloading csv file with statistics about all users from the team

            Parameters:
                    request: Request to process
                    pk: Team id

            Returns:
                    Rendered view
    """
    team = Team.objects.get(pk=pk)
    users = team.users.all() | team.admins.all()

    data = json.dumps([{'user': o.user.username,
                        'metrics': o.metrics,
                        'time_from': str(o.time_from),
                        'time_to': str(o.time_to)}
                       for o in list(UserStat.objects.filter(user__in=users))])
    df = pd.read_json(data)
    metrics_df = pd.json_normalize(df['metrics'])
    del df['metrics']
    df = pd.concat([df, metrics_df], axis=1)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=filename.csv'
    df.to_csv(path_or_buf=response, sep=';', float_format='%.2f', index=False, decimal=",")
    return response
