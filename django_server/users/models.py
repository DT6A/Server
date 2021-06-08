from abc import abstractmethod
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.core.management.utils import get_random_secret_key
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Cast
from django.utils import timezone


class UserStat(models.Model):
    """
    User statistics

    Attributes:
    ----------
    metrics :
        Data about metrics
    time_from :
        Date tracked from
    time_to :
        Date tracked to
    user :
        User about whom records
    """
    metrics = models.JSONField(default=dict)
    time_from = models.DateTimeField(default=timezone.now())
    time_to = models.DateTimeField(default=timezone.now())
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class UserUniqueToken(models.Model):
    """
    User private unique token for interacting with plugin

    Attributes
    ----------
    user :
        Token owner
    token :
        Random token string
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, default=get_random_secret_key)


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


class Profile(models.Model):
    """
    User profile with additional information

    Attributes
    ----------

    user :
        Profile owner
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # image = models.ImageField(default='default.jpg', upload_to='profile_pics')

    def __str__(self):
        return f'{self.user.username} Profile'

    @staticmethod
    def aggregate_lines(filtered):
        return \
            filtered.annotate(lines_value=Cast(KeyTextTransform('lines', 'metrics'), models.IntegerField())).aggregate(
                Sum('lines_value'))['lines_value__sum']

    @property
    def stats_for_all_time(self):
        s = self.aggregate_lines(UserStat.objects.filter(user=self.user))
        return s if s else 0

    def lines_written_within_delta(self, delta):
        s = self.aggregate_lines(UserStat.objects.filter(user=self.user, time_from__gte=datetime.now() - delta))
        return s if s else 0

    @property
    def stats_for_last_year(self):
        return self.lines_written_within_delta(timedelta(days=365))

    @property
    def stats_for_last_month(self):
        return self.lines_written_within_delta(timedelta(days=30))

    @property
    def stats_for_last_week(self):
        return self.lines_written_within_delta(timedelta(days=7))

    @property
    def stats_for_last_day(self):
        return self.lines_written_within_delta(timedelta(days=1))


class Metric(models.Model):
    """
    Metric representation

    Attributes
    ----------
    name :
        Metric name
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        if hasattr(self, 'charcountingmetric'):
            return str(self.charcountingmetric)
        elif hasattr(self, 'substringcountingmetric'):
            return str(self.substringcountingmetric)


class CharCountingMetric(Metric):
    """
    Metric for counting characters

    Attributes
    ----------
    char :
        Character to count
    """
    char = models.CharField(max_length=1, unique=True, blank=False)

    def __str__(self):
        return 'Number of \"' + str(self.char) + '\" characters'


class SubstringCountingMetric(Metric):
    """
    Metric for counting substrings

    Attributes
    ----------
    substring :
        Substring to count
    """
    substring = models.CharField(max_length=100, unique=True, blank=False)

    def __str__(self):
        return 'Number of \"' + str(self.substring) + '\" substrings'


class Team(models.Model):
    """
    Team of users

    Attributes
    ----------
    name :
        Team name
    users :
        Team members
    admins :
        Team administrators
    invite_key :
        Team invitation key
    tracked_metrics :
        Metrics tracked within the team
    """
    name = models.CharField(max_length=100, unique=True)
    users = models.ManyToManyField(User, related_name='team_user', blank=True)
    admins = models.ManyToManyField(User, related_name='team_admin')
    invite_key = models.CharField(max_length=100, default=get_random_secret_key)
    tracked_metrics = models.ManyToManyField(Metric, related_name='metrics', blank=True)

    def __str__(self):
        return self.name


class Achievement(models.Model):
    name = models.CharField(max_length=100, unique=True)
    assigned_users = models.ManyToManyField(User, related_name="unfinished_achievements", blank=False)
    completed_users = models.ManyToManyField(User, related_name="finished_achievements", blank=True)
    metric_to_goal = models.JSONField(default=dict)

    def __str__(self):
        return self.name

