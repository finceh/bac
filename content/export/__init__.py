# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import csv
from cStringIO import StringIO

from openpyxl import Workbook


class Formatter(object):
    content_type = None

    def __init__(self):
        if self.content_type is None:
            msg = 'content_type of %s is None' % self.__class__.__name__
            raise NotImplementedError(msg)

    def format(self, items):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        return self.format(*args, **kwargs)


class XLSXFormatter(Formatter):
    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def format(self, items):
        wb = Workbook(write_only=True)
        ws = wb.create_sheet()
        for item in items:
            ws.append(item)

        content = StringIO()
        wb.save(filename=content)
        return content.getvalue()


class CSVFormatter(Formatter):
    content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def __init__(self, encoding='utf-8'):
        self.encoding = encoding

    def _encode(self, value):
        try:
            return value.encode(self.encoding)
        except AttributeError:
            return value

    def _encode_row(self, row):
        return [self._encode(v) for v in row]

    def format(self, items, header=None):
        content = StringIO()
        writer = csv.writer(content, delimiter=str(';'))
        if header:
            writer.writerow(self._encode_row(header))

        for item in items:
            writer.writerow(self._encode_row(item))
        return content.getvalue()


as_xlsx = XLSXFormatter()
as_csv = CSVFormatter()


class FormatPool(object):
    def __init__(self, msg='Wrong format: {fmt}; choices are {choices}',
                 **formats):
        self.msg = msg
        self.formats = formats

    def __call__(self, fmt):
        try:
            return self.formats[fmt]
        except KeyError:
            raise ValueError(self.msg.format(fmt=fmt,
                                             choices=', '.join(self.formats)))

get_formatter = FormatPool(xslx=as_xlsx, csv=as_csv)
