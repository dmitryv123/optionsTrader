from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Instrument, IbkrContract, Portfolio, Position, Order, Execution, OptionEvent

admin.site.register(Instrument)
admin.site.register(IbkrContract)
admin.site.register(Portfolio)
admin.site.register(Position)
admin.site.register(Order)
admin.site.register(Execution)
admin.site.register(OptionEvent)
