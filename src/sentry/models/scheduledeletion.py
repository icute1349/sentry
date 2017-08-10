from __future__ import absolute_import

from datetime import timedelta
from django.db import models
from django.db.models import get_model
from django.utils import timezone
from jsonfield import JSONField
from uuid import uuid4

from sentry.db.models import BoundedBigIntegerField, Model


class ScheduledDeletion(Model):
    __core__ = False

    guid = models.CharField(max_length=32, unique=True, default=lambda: uuid4().hex)
    app_label = models.CharField(max_length=64)
    model_name = models.CharField(max_length=64)
    object_id = BoundedBigIntegerField()
    date_added = models.DateTimeField(default=timezone.now)
    date_scheduled = models.DateTimeField(default=lambda: (timezone.now() + timedelta(days=30)))
    actor_id = BoundedBigIntegerField(null=True)
    data = JSONField(default={})
    in_progress = models.BooleanField(default=False)
    aborted = models.BooleanField(default=False)

    class Meta:
        unique_together = (('app_label', 'model_name', 'object_id'), )
        app_label = 'sentry'
        db_table = 'sentry_scheduleddeletion'

    @classmethod
    def schedule(cls, instance, days=30, data={}, actor=None):
        return cls.objects.create(
            app_label=instance._meta.app_label,
            model_name=type(instance).__name__,
            object_id=instance.pk,
            date_scheduled=timezone.now() + timedelta(days=days),
            data=data,
            actor_id=actor.id if actor else None,
        )

    def get_model(self):
        return get_model(self.app_label, self.model_name)

    def get_instance(self):
        return self.get_model().objects.get(pk=self.object_id)

    def get_actor(self):
        from sentry.models import User

        if not self.actor_id:
            return None

        try:
            return User.objects.get(id=self.actor_id)
        except User.DoesNotExist:
            return None
