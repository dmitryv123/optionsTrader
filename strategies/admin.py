# Register your models here.

from django.contrib import admin
from .models import (
    StrategyDefinition,
    StrategyVersion,
    StrategyInstance,
    StrategyRun,
    Signal,
    Recommendation,
    Opportunity,
)

admin.site.register(StrategyDefinition)
admin.site.register(StrategyVersion)
admin.site.register(StrategyInstance)
admin.site.register(StrategyRun)
admin.site.register(Signal)
admin.site.register(Recommendation)
admin.site.register(Opportunity)
