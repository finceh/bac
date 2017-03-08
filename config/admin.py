# -*- coding: utf-8 -*-
from django.contrib import admin
from solo.admin import SingletonModelAdmin

from content.models import Customer
from config.models import SiteConfiguration


class SiteConfigurationAdmin(SingletonModelAdmin):
    readonly_fields = ('get_cards_available',)
    fieldsets = (('Диапазон карт', {'fields': (('card_start', 'card_end'),
                                               'get_cards_available')}),
                 (None, {'fields': (('lower_limit', 'increase_by',),)}),
                 (None, {'fields': ('email_subject',)}),)

    def get_cards_available(self, obj):
        return Customer.objects.avail_cards_count()

    get_cards_available.short_description = 'Доступно карт'


admin.site.register(SiteConfiguration, SiteConfigurationAdmin)
