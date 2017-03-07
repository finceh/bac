# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import date, timedelta

from django.db import models
from django.contrib import admin
from django.contrib.admin.options import IncorrectLookupParameters
from django.http import HttpResponseBadRequest, HttpResponse, Http404
from django.utils import timezone
from django.conf.urls import url

from content.export import customer as export
from content.models import Customer, Text, EmailTask, Service
from content.views.admin import ImportView, CleanView


class TextAdmin(admin.ModelAdmin):
    list_display = ('id', 'place', 'is_active')
    list_filter = ('is_active', 'place')
admin.site.register(Text, TextAdmin)


class ServiceAdmin(admin.ModelAdmin):
    list_display = ('image', 'text', 'order', 'is_active')
    list_filter = ('is_active',)
admin.site.register(Service, ServiceAdmin)


class HasCardFilter(admin.SimpleListFilter):
    title = 'Карта'
    parameter_name = 'has_card'

    def lookups(self, request, model_admin):
        return ((1, 'Есть'),
                (0, 'Нет'))

    def queryset(self, request, queryset):
        value = self.value()
        try:
            value = int(value)
        except (ValueError, TypeError):
            return queryset
        func = queryset.filter if value == 0 else queryset.exclude
        return func(card=None)


class DateFieldListFilter(admin.DateFieldListFilter):
    def __init__(self, *args, **kwargs):
        super(DateFieldListFilter, self).__init__(*args, **kwargs)
        today = self.links[1][1][self.lookup_kwarg_since]
        yesterday = date(*map(int, today.split(' ', 1)[0].split('-'))) \
                    - timedelta(days=1)
        links = list(self.links)
        links.insert(2, ('Вчера', {self.lookup_kwarg_since: str(yesterday),
                                   self.lookup_kwarg_until: today}))
        self.links = tuple(links)

DateFieldListFilter.register(lambda f: isinstance(f, models.DateField),
                             DateFieldListFilter,
                             take_priority=True)


class CustomerAdmin(admin.ModelAdmin):
    readonly_fields = ('utm_link',)
    list_display = ('when_created', 'card_name', 'last_name',
                    'first_name', 'middle_name', 'email', 'phone', 'ins_end',
                    'email_status', 'utm_link')
    list_filter = (HasCardFilter, 'email_status', 'when_created', 'ins_end')

    def get_urls(self):
        urls = super(CustomerAdmin, self).get_urls()
        return [url(r'^export/(?P<fmt>\w+)/$',
                    self.admin_site.admin_view(self.export),
                    name='export_customers'),
                url('^import/xlsx/$',
                    self.admin_site.admin_view(ImportView.as_view()),
                    name='import_customers'),
                url('^clean/$',
                    self.admin_site.admin_view(CleanView.as_view()),
                    name='clean_customers')] + urls

    def card_name(self, obj):
        return obj.get_card_name()
    card_name.short_description = 'Карта'

    def export(self, request, fmt):
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        list_filter = self.get_list_filter(request)
        search_fields = self.get_search_fields(request)
        list_select_related = self.get_list_select_related(request)

        ChangeList = self.get_changelist(request)
        try:
            cl = ChangeList(
                request, self.model, list_display,
                list_display_links, list_filter, self.date_hierarchy,
                search_fields, list_select_related, self.list_per_page,
                self.list_max_show_all, self.list_editable, self,
            )
        except IncorrectLookupParameters:
            return HttpResponseBadRequest('Incorrect lookup parameters')

        qs = cl.get_queryset(request)
        try:
            fmtr = export.get_formatter(fmt)
        except ValueError, e:
            raise Http404

        response = HttpResponse(content_type=fmtr.content_type,
                                content=fmtr(qs.iterator()))
        now = timezone.now().strftime('%Y_%m_%d_%H_%M')
        cdisp = 'attachment; filename="customers_%s.%s' % (now, fmt)
        response['Content-Disposition'] = cdisp
        return response
admin.site.register(Customer, CustomerAdmin)


class EmailTaskAdmin(admin.ModelAdmin):
    list_display = ('when_created', 'when_sent', 'when_opened', 'customer')
admin.site.register(EmailTask, EmailTaskAdmin)
