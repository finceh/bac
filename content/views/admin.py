# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
from cStringIO import StringIO

from django.http import HttpResponse
from django.views.generic.base import ContextMixin
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.views.generic import View
from django.shortcuts import render
from django.utils import timezone
from django.contrib import admin
from django.apps import apps
from openpyxl import Workbook, load_workbook

from content.models import Customer, EmailStatus, EmailTask
from content.forms import ImportForm


class HttpResponseSeeOther(HttpResponse):
    def __init__(self, *args, **kwargs):
        location = kwargs.pop('location', None)
        kwargs['status'] = 303
        super(HttpResponseSeeOther, self).__init__(*args, **kwargs)
        if location is not None:
            self['Location'] = location


class AdminContextMixin(ContextMixin):
    title = ''

    def get_context_data(self, **kwargs):
        kwargs.update(admin.site.each_context(self.request))
        kwargs.setdefault('title', self.title)
        return super(AdminContextMixin, self).get_context_data(**kwargs)


class CustomerContextMixin(AdminContextMixin):
    def get_context_data(self, **kwargs):
        kwargs['app'] = apps.get_app_config('content')
        kwargs['model_name'] = Customer._meta.verbose_name_plural
        return super(CustomerContextMixin, self).get_context_data(**kwargs)


class HasPermMixin(CustomerContextMixin):
    permissions = None
    no_perms_template = 'admin/no_perms.html'

    def __init__(self, *args, **kwargs):
        super(HasPermMixin, self).__init__(*args, **kwargs)
        if self.permissions is None:
            msg = '%s: permissions is None' % self.__class__.__name__
            raise ImproperlyConfigured(msg)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perms(self.permissions):
            return render(request, self.no_perms_template, status=403,
                          context=self.get_context_data())
        return super(HasPermMixin, self).dispatch(request, *args, **kwargs)


class CleanPermMixin(HasPermMixin):
    permissions = ['content.delete_customer', 'content.delete_emailtask']


class ImportView(CleanPermMixin, View):
    template_name = 'admin/import_customers.html'
    title = 'Импорт пользователей'

    def get(self, request):
        return render(request, self.template_name,
                      self.get_context_data(form=ImportForm()))

    def post(self, request):
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            wb = load_workbook(request.FILES['data'], read_only=True)
            ws = wb.active
            ids = {v: k for k, v in EmailStatus._DISPLAY.iteritems()}
            customers = []
            errors = set()
            card_re = re.compile(r'.*?(\d+)$')
            for row in ws.rows:
                c = {k: row[i].value for i, k in enumerate(('when_created',
                                                            'card',
                                                            'last_name',
                                                            'first_name',
                                                            'middle_name',
                                                            'email',
                                                            'phone',
                                                            'ins_end',
                                                            'email_status',
                                                            'source',
                                                            'utm_link'))}
                del c['source']
                if c['card']:
                    m = card_re.match(c['card'])
                    if m:
                        c['card'] = int(m.group(1))
                    else:
                        errors.add('Неправильный формат карты: %s' % c['card'])
                        continue
                try:
                    c['email_status'] = ids[row[8].value]
                except IndexError:
                    errors.add(('Не указан статус письма',))
                    continue
                except KeyError:
                    errors.add(('Неверно указан статус письма', row[8].value))
                    continue
                customers.append(Customer(**c))

            if errors:
                for err in errors:
                    form.add_error(None, ': '.join(err))
            else:
                EmailTask.objects.all().delete()
                Customer.objects.all().delete()
                Customer.objects.bulk_create(customers)
                return HttpResponseSeeOther(
                    location=reverse('admin:content_customer_changelist')
                )
        return render(request, self.template_name, status=400,
                      context=self.get_context_data(form=form))


class CleanView(CleanPermMixin, View):
    title = 'Обнулить'

    def get(self, request):
        return render(request, 'admin/confirm_clean.html',
                      self.get_context_data())

    def post(self, request):
        EmailTask.objects.all().delete()
        Customer.objects.all().delete()
        return HttpResponseSeeOther(
            location=reverse('admin:content_customer_changelist')
        )
