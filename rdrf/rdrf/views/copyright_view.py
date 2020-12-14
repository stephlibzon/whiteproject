from django.shortcuts import render
from django.views.generic.base import View

from rdrf.models.definition.models import Registry
from rdrf.models.proms.models import Survey
from rdrf.helpers.utils import LoginRequiredMixin


import logging

logger = logging.getLogger(__name__)


class CopyrightView(View, LoginRequiredMixin):

    def get(self, request):
        registry_models = Registry.objects.all()
        contexts = []
        no_copyright = "No Copyright information available"
        for registry in registry_models:
            copyright_dict = {}
            registry_copyright_text = registry.metadata.get("copyright_text", no_copyright)
            for survey_model in Survey.objects.filter(registry=registry):
                for survey_question in survey_model.survey_questions.all():
                    if survey_question.copyright_text and survey_question.source:
                        copyright_dict.update({
                            survey_question.source: survey_question.copyright_text,
                        })
            context = {
                "copyright_dict": copyright_dict,
                "registry_name": registry.name,
                "registry_copyright": registry_copyright_text,
            }
            contexts.append(context)

        data = {
            "contexts": contexts,
        }
        return render(request, "rdrf_cdes/copyright.html", data)
