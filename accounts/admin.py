from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Client, ClientMembership, BrokerAccount, AccountSnapshot

admin.site.register(Client)
admin.site.register(ClientMembership)
admin.site.register(BrokerAccount)
admin.site.register(AccountSnapshot)