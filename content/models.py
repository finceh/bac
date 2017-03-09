# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core import validators
from django.dispatch import receiver
from django.core.mail.message import EmailMultiAlternatives
from django.template import Context, Template, loader
from django.utils.crypto import get_random_string
from django.db.models.signals import pre_save, post_save
from dateutil.relativedelta import relativedelta
from ckeditor.fields import RichTextField

from config.models import SiteConfiguration
from django.db.models import F


class ActiveManager(models.Manager):
    def active(self, *args, **kwargs):
        kwargs['is_active'] = True
        return self.filter(*args, **kwargs)


class Text(models.Model):
    class Meta:
        verbose_name = 'Текстовый блок'
        verbose_name_plural = 'Текстовые блоки'

    class PLACE:
        INFO = 'info'
        INTRO = 'intro'
        MOTIVATE = 'motivate'
        FOOTER = 'footer'
        EMAIL = 'email'
        SUCCESS = 'success'
        _CHOICES = ((INFO, 'Информационный блок'),
                    (INTRO, 'Вводный текст'),
                    (MOTIVATE, 'Мотивационный элемент'),
                    (FOOTER, 'Текст футера'),
                    (EMAIL, 'Email'),
                    (SUCCESS, 'Страница благодарности'))
        _ALL = {item[0] for item in _CHOICES}

    def __unicode__(self):
        return self.get_place_display()

    objects = ActiveManager()

    place = models.CharField('Место', choices=PLACE._CHOICES, max_length=20)
    is_active = models.BooleanField('Активен', default=False,
                                    help_text='Выбор этой опции сделает неактивным другой текст на этом месте.')
    text = RichTextField('Текст',
        help_text="""Для страницы благодарности и письма доступны переменные:
    {{ last_name }} - фамилия;
    {{ first_name }} - имя;
    {{ middle_name }} - отчество;
    {{ phone }} - номер телефона;
    {{ email }} - электронная почта;
    {{ card }} - карта.
    """)

    def get_template_context(self, customer):
        ctx = {}
        for attr in ('first_name', 'middle_name', 'last_name',
                     'phone', 'email'):
            ctx[attr] = getattr(customer, attr)
        ctx['card'] = customer.get_card_name()
        return ctx

    def render(self, data=None):
        tpl = Template(self.text)
        ctx = data or {}
        if isinstance(ctx, Customer):
            ctx = self.get_template_context(data)
        return tpl.render(Context(ctx))


class Service(models.Model):
    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ('order', 'id')

    class Image:
        EVAC = 'evac'
        ACCUM = 'accum'
        GAS = 'gas'
        CALL = 'call'

        _CHOICES = ((EVAC, 'Эвакуатор'),
                    (ACCUM, 'Аккумулятор'),
                    (GAS, 'Топливо'),
                    (CALL, 'Консультация'))

        _FILES = {EVAC: 'ico_01.png',
                  ACCUM: 'ico_02.png',
                  GAS: 'ico_03.png',
                  CALL: 'ico_04.png'}

    def __unicode__(self):
        return self.get_image_display()

    objects = ActiveManager()

    text = RichTextField('Текст')
    image = models.CharField('Изображение', choices=Image._CHOICES,
                             max_length=10)
    order = models.IntegerField('Порядок', default=0)
    is_active = models.BooleanField('Активен', default=True)

    def get_filename(self):
        return os.path.join('img', self.Image._FILES[self.image])


class EmailStatus:
    FAILED = -1
    NOT_EXIST = 0
    CREATED = 1
    SENT = 2
    OPENED = 3
    _CHOICES = ((NOT_EXIST, 'Не существует'),
                (CREATED, 'Создано'),
                (SENT, 'Отправлено'),
                (OPENED, 'Открыто'),
                (FAILED, 'Не удалось отправить'))
    _DISPLAY = dict(_CHOICES)


class CustomerManager(models.Manager):
    def has_cards(self, *args, **kwargs):
        return self.exclude(card=None).filter(*args, **kwargs)

    def existing_cards(self, *args, **kwargs):
        return self.has_cards(*args, **kwargs).values_list('card', flat=True)

    def avail_cards_count(self):
        conf = SiteConfiguration.get_solo()
        exist = self.has_cards(card__gte=conf.card_start,
                               card__lte=conf.card_end).count()
        return conf.get_cards_count() - exist


class Customer(models.Model):
    PHONE_RE = r'^0\d{9}$'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __unicode__(self):
        return self.get_full_name()

    objects = CustomerManager()

    when_created = models.DateTimeField('Дата регистрации', auto_now_add=True)
    first_name = models.CharField('Имя', max_length=50)
    middle_name = models.CharField('Отчество', max_length=50)
    last_name = models.CharField('Фамилия', max_length=50)
    email = models.EmailField(unique=True)
    phone = models.CharField('Телефон', max_length=10, unique=True,
                             validators=[
                                 validators.RegexValidator(PHONE_RE)
                             ])
    ins_end = models.DateField('Дата окончания ОСАГО')
    card = models.PositiveIntegerField('Номер карты', unique=True,
                                       blank=True, null=True)
    email_status = models.IntegerField('Письмо', choices=EmailStatus._CHOICES,
                                       default=EmailStatus.NOT_EXIST)
    utm_link = models.URLField('Ссылка UTM', blank=True)

    def get_full_name(self):
        return ' '.join((self.last_name, self.first_name, self.middle_name))

    def card_valid_since(self, delay=1):
        return self.when_created.date() + timedelta(days=delay)

    def card_valid_till(self, months=3):
        return self.card_valid_since() + relativedelta(months=months)

    def get_card_name(self):
        if self.card is None:
            return ''
        return 'UV %i' % self.card


class EmailTask(models.Model):
    class Meta:
        verbose_name = 'Письмо'
        verbose_name_plural = 'Письма'
        ordering = ('-when_created',)

    def __unicode__(self):
        return self.get_status_display()

    customer = models.ForeignKey(Customer, verbose_name='Пользователь',
                                 related_name='emails')
    when_created = models.DateTimeField('Дата создания', auto_now_add=True)
    when_sent = models.DateTimeField('Дата отправки', blank=True, null=True)
    when_opened = models.DateTimeField('Дата открытия', blank=True, null=True)
    token = models.CharField('Токен', max_length=12, default=get_random_string,
                             unique=True)

    def get_status(self):
        if self.when_opened:
            return EmailStatus.OPENED
        if self.when_sent:
            return EmailStatus.SENT
        return EmailStatus.CREATED

    def get_status_display(self):
        return EmailStatus._DISPLAY[self.get_status()]


@receiver(pre_save, sender=Customer)
def on_customer_create(sender, instance, **kwargs):
    if instance.id or instance.card:
        return
    conf = SiteConfiguration.get_solo()
    existing_cards = set(Customer.objects.existing_cards())
    for card in conf.get_cards_range():
        if card not in existing_cards:
            instance.card = card
            break
    if Customer.objects.avail_cards_count() <= conf.lower_limit:
        conf.card_end = F('card_end') + conf.increase_by
        conf.save()


@receiver(post_save, sender=Customer)
def on_new_customer_saved(sender, instance, created, **kwargs):
    if not created:
        return
    EmailTask.objects.create(customer=instance)


@receiver(post_save, sender=EmailTask)
def on_email_task_save(sender, instance, created, **kwargs):
    if created:
        try:
            tpl = Text.objects.active().get(place=Text.PLACE.EMAIL)
        except Text.DoesNotExist:
            return
        ctx = tpl.get_template_context(instance.customer)
        text = tpl.render(data=ctx)
        ctx['msg'] = text
        ctx['token'] = instance.token
        ctx['site_url'] = settings.SITE_URL
        tpl = loader.get_template('email_card.html')
        text = tpl.render(Context(ctx))
        conf = SiteConfiguration.get_solo()
        msg = EmailMultiAlternatives(subject=conf.email_subject,
                                     body=text, to=[instance.customer.email],
                                     from_email=settings.DEFAULT_FROM_EMAIL)
        msg.attach_alternative(text, 'text/html')
        try:
            msg.send(fail_silently=False)
        except:
            instance.customer.email_status = EmailStatus.FAILED
        else:
            instance.customer.email_status = EmailStatus.SENT
            instance.when_sent = timezone.now()
            instance.save()
        finally:
            instance.customer.save()
    else:
        if instance.when_opened \
                and instance.customer.email_status != EmailStatus.OPENED:
            instance.customer.email_status = EmailStatus.OPENED
            instance.customer.save()


@receiver(pre_save, sender=Text)
def on_text_save(sender, instance, **kwargs):
    if instance.is_active:
        sender.objects.filter(place=instance.place).update(is_active=False)
