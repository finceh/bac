from django.conf import settings
from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import View
from django.core.exceptions import ValidationError
from django.views.generic.base import ContextMixin
from django.views.decorators.http import require_GET

from content.models import Text, EmailTask, Service, Customer
from content.forms import CustomerForm, EmailTokenForm


class LandingView(ContextMixin, View):
    def get_context_data(self, **kwargs):
        ctx = super(LandingView, self).get_context_data(**kwargs)
        ctx['services'] = Service.objects.active()
        ctx['texts'] = {t.place: t for t in Text.objects.active()}
        ctx['cards_avail'] = Customer.objects.avail_cards_count()
        return ctx

    def get(self, request):
        return render(request, 'index.html',
                      self.get_context_data(form=CustomerForm()))

    def post(self, request):
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.cleaned_data
            customer['last_name'],\
            customer['first_name'],\
            customer['middle_name'] = customer.pop('fullname').split()
            customer['utm_link'] = request.session.get('utm')
            customer = Customer(**customer)
            try:
                customer.validate_unique()
            except ValidationError, e:
                for field, msg in e.message_dict.iteritems():
                    form.add_error(field, msg)
            else:
                customer.save()
                try:
                    tpl = Text.objects.active().get(place=Text.PLACE.SUCCESS)
                except Text.DoesNotExist:
                    msg = None
                else:
                    msg = tpl.render(data=customer)
                return render(request, 'index.html', {'msg': msg, 'valid': True})
        return render(request, 'index.html', self.get_context_data(form=form),
                      status=400)


@require_GET
def email_opened(request):
    form = EmailTokenForm(request.GET)
    if form.is_valid():
        try:
            email = EmailTask.objects.get(when_opened=None,
                                          token=form.cleaned_data['token'])
        except EmailTask.DoesNotExist:
            pass
        else:
            email.when_opened = timezone.now()
            email.save()

    with open(settings.DUMMY_IMAGE) as f:
        img = f.read()
    return HttpResponse(content=img, content_type='image/png')
