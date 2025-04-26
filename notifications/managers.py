from django.db import models, transaction
from django.dispatch import Signal


# Custom signal for bulk post save
bulk_post_save = Signal()


class SignalTriggeringManager(models.Manager):
    def bulk_create(self, instances, batch_size=300, **kwargs):
        with transaction.atomic():
            results = super().bulk_create(instances, batch_size=batch_size, **kwargs)

            # Emit custom bulk signal
            self.call_bulk_signal(instances=results, created=True)

            return results

    def bulk_update(self, instances, fields, batch_size=300, **kwargs):
        with transaction.atomic():
            results = super().bulk_update(
                instances, fields, batch_size=batch_size, **kwargs
            )

            # Emit custom bulk signal
            self.call_bulk_signal(instances=instances, created=False)

            return results

    def call_bulk_signal(self, instances, created=True):
        if not instances:
            return

        model_class = instances[0].__class__
        bulk_post_save.send(sender=model_class, instances=instances, created=created)
