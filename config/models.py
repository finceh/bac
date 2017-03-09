# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from solo.models import SingletonModel


class SiteConfiguration(SingletonModel):
    class Meta:
        verbose_name = 'Настройки сайта'

    def __unicode__(self):
        return 'Настройки сайта'

    card_start = models.PositiveIntegerField('От', default=1)
    card_end = models.PositiveIntegerField('До', default=200,
                                           help_text='включительно')
    email_subject = models.CharField('Тема письма', max_length=255,
                                     default='Поздравляем!')
    lower_limit = models.PositiveIntegerField(verbose_name='Увеличивать диапазон карт при достижении их числа',
                                              default=10)
    increase_by = models.PositiveIntegerField(verbose_name='Увеличивать диапазон на', default=200)

    def get_cards_range(self):
        return xrange(self.card_end, self.card_start - 1, -1)

    def get_cards_count(self):
        return self.card_end - self.card_start + 1
