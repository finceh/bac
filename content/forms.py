# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django import forms
from django.core.validators import RegexValidator

from content.models import Customer


class CustomerForm(forms.Form):
    fullname = forms.CharField(
        label='Ваше ФИО',
        max_length=152,
        validators=[
            RegexValidator(r'^(?:[^\s]+\s+){2}(?:[^\s]+)$')
        ]
    )
    ins_end = forms.DateField(label='Когда у вас оканчивается ОСАГО',
                              input_formats=('%m/%d/%Y',))
    email = forms.EmailField()
    phone = forms.CharField(max_length=10, min_length=10,
                            validators=[RegexValidator(Customer.PHONE_RE)])


class ImportForm(forms.Form):
    data = forms.FileField(label='Пользователи')


class EmailTokenForm(forms.Form):
    token = forms.CharField(label='Токен',
                            validators=[RegexValidator(r'^[\w\d]{12}$')])
