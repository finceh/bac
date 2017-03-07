# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from itertools import imap
from django.conf import settings
from content.export import XLSXFormatter, CSVFormatter, FormatPool


class CustomerXLSXFormatter(XLSXFormatter):
    def _get_row(self, obj):
        return (obj.when_created, obj.get_card_name(), obj.last_name, obj.first_name,
                obj.middle_name, obj.email, obj.phone,
                obj.ins_end, obj.get_email_status_display(),
                settings.DATA_SOURCE, obj.utm_link)

    def format(self, items):
        items = imap(self._get_row, items)
        return super(CustomerXLSXFormatter, self).format(items)


class CustomerCSVFormatter(CSVFormatter):
    def _format_date(self, value):
        return value.strftime('%d.%m.%Y')

    def _get_row(self, obj):
        return (obj.get_full_name(), obj.phone, obj.email,
                self._format_date(obj.ins_end), obj.get_card_name(),
                self._format_date(obj.card_valid_since()),
                self._format_date(obj.card_valid_till()),
                settings.DATA_SOURCE, obj.utm_link)

    def format(self, items, header=('Название лида', 'Мобильный телефон',
                                    'Частный e-mail', 'Дата окончания ОСАГО',
                                    'Номер карты ЮА', 'Дата начала карты ЮА',
                                    'Дата окончания карты ЮА', 'Источник', 'Канал')):
        items = imap(self._get_row, items)
        return super(CustomerCSVFormatter, self).format(items, header=header)


as_xlsx = CustomerXLSXFormatter()
as_csv = CustomerCSVFormatter()

get_formatter = FormatPool(xlsx=as_xlsx, csv=as_csv)
