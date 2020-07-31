import os
import pycountry
import subprocess
from datetime import datetime
import json

from django.db.models import Q
from rest_framework import generics
from rest_framework import viewsets
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from registry.genetic.models import Gene, Laboratory
from registry.patients.models import Patient, Registry, Doctor, NextOfKinRelationship
from registry.groups.models import CustomUser, WorkingGroup
from rdrf.services.rest.serializers import PatientSerializer, RegistrySerializer, WorkingGroupSerializer, CustomUserSerializer, DoctorSerializer, NextOfKinRelationshipSerializer
from celery.result import AsyncResult
from django.http import HttpResponse
from rdrf.models.task_models import CustomActionExecution

import logging
logger = logging.getLogger(__name__)


class BadRequestError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST


class RegistryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Registry.objects.all()
    serializer_class = RegistrySerializer
    lookup_field = 'code'


class RegistryList(generics.ListCreateAPIView):
    queryset = Registry.objects.all()
    serializer_class = RegistrySerializer


class DoctorDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer


class NextOfKinRelationshipDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = NextOfKinRelationship.objects.all()
    serializer_class = NextOfKinRelationshipSerializer


class NextOfKinRelationshipViewSet(viewsets.ModelViewSet):
    queryset = NextOfKinRelationship.objects.all()
    serializer_class = NextOfKinRelationshipSerializer


class PatientDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = (IsAuthenticated,)

    def _get_registry_by_code(self, registry_code):
        try:
            return Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            raise BadRequestError("Invalid registry code '%s'" % registry_code)

    def check_object_permissions(self, request, patient):
        """We're always filtering the patients by the registry code form the url and the user's working groups"""
        super(PatientDetail, self).check_object_permissions(request, patient)
        registry_code = self.kwargs.get('registry_code')
        registry = self._get_registry_by_code(registry_code)
        if registry not in patient.rdrf_registry.all():
            self.permission_denied(
                request, message='Patient not available in requested registry')
        if request.user.is_superuser:
            return
        if registry not in request.user.registry.all():
            self.permission_denied(
                request, message='Not allowed to get Patients from this Registry')

        if not patient.working_groups.filter(pk__in=request.user.working_groups.all()).exists():
            self.permission_denied(request, message='Patient not in your working group')


class PatientList(generics.ListCreateAPIView):

    serializer_class = PatientSerializer

    def _get_registry_by_code(self, registry_code):
        try:
            return Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            raise BadRequestError("Invalid registry code '%s'" % registry_code)

    def get_queryset(self):
        """We're always filtering the patients by the registry code form the url and the user's working groups"""
        registry_code = self.kwargs.get('registry_code')
        registry = self._get_registry_by_code(registry_code)
        if self.request.user.is_superuser:
            return Patient.objects.get_by_registry(registry.pk)
        return Patient.objects.get_by_registry_and_working_group(registry, self.request.user)

    def post(self, request, *args, **kwargs):
        registry_code = kwargs.get('registry_code')
        if len(request.data) > 0:
            # For empty posts don't set the registry as it fails because request.data
            # is immutable for empty posts. Post request will fail on validation anyways.

            request.data['registry'] = self._get_registry_by_code(registry_code)
        if not (
                request.user.is_superuser or request.data['registry'] in request.user.registry.all()):
            self.permission_denied(
                request, message='Not allowed to create Patient in this Registry')
        return super(PatientList, self).post(request, *args, **kwargs)


class RegistryViewSet(viewsets.ModelViewSet):
    queryset = Registry.objects.all()
    serializer_class = RegistrySerializer
    lookup_field = 'code'

    # Overriding get_object to make registry lookup be based on the registry code
    # instead of the pk
    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        obj = generics.get_object_or_404(queryset, code=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)

        return obj


class WorkingGroupViewSet(viewsets.ModelViewSet):
    queryset = WorkingGroup.objects.all()
    serializer_class = WorkingGroupSerializer


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer


class ListCountries(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, format=None):
        countries = sorted(pycountry.countries, key=lambda c: c.name)

        def to_dict(country):
            # wanted_fields = ('name', 'alpha_2', 'alpha_3', 'numeric', 'official_name')
            wanted_fields = ('name', 'numeric', 'official_name')
            aliases = {
                'alpha_2': 'country_code',
                'alpha_3': 'country_code3',
            }

            d = dict([(k, getattr(country, k, None)) for k in wanted_fields])
            for attr, alias in aliases.items():
                d[alias] = getattr(country, attr)
            d['states'] = reverse('state_lookup', args=[country.alpha_2], request=request)

            return d

        return Response(list(map(to_dict, countries)))


class ListStates(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, country_code, format=None):
        try:
            subdivisions = pycountry.subdivisions.get(
                country_code=country_code)
            if subdivisions:
                states = sorted(subdivisions, key=lambda x: x.name)
            else:
                states = []
        except KeyError:
            # For now returning empty list because the old api view was doing the same
            # raise BadRequestError("Invalid country code '%s'" % country_code)
            states = []

        wanted_fields = ('name', 'code', 'type', 'country_code')

        def to_dict(x):
            return dict([(k, getattr(x, k)) for k in wanted_fields])

        return Response(list(map(to_dict, states)))


class ListClinicians(APIView):
    queryset = CustomUser.objects.none()
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, registry_code, format=None):
        users = CustomUser.objects.filter(registry__code=registry_code, is_superuser=False)
        clinicians = [u for u in users if u.is_clinician]

        def to_dict(c, wg):
            return {
                'id': "%s_%s" % (reverse(
                    'v1:customuser-detail',
                    args=[
                        c.id,
                    ]),
                    reverse(
                    'v1:workinggroup-detail',
                    args=[
                        wg.id,
                    ])),
                'full_name': "%s %s (%s)" % (c.first_name,
                                             c.last_name,
                                             wg.name),
            }

        return Response([to_dict(c, wg) for c in clinicians for wg in c.working_groups.all()])


class LookupGenes(APIView):
    queryset = Gene.objects.none()

    def get(self, request, format=None):
        query = None
        try:
            query = request.GET['term']
        except KeyError:
            pass
            # raise BadRequestError("Required query parameter 'term' not received")

        def to_dict(gene):
            return {
                'value': gene.symbol,
                'label': gene.name,
            }

        genes = None
        if query is None:
            genes = Gene.objects.all()
        else:
            genes = Gene.objects.filter(symbol__icontains=query)
        return Response(list(map(to_dict, genes)))


class LookupLaboratories(APIView):
    queryset = Laboratory.objects.none()

    def get(self, request, format=None):
        query = None
        try:
            query = request.GET['term']
        except KeyError:
            pass
            # raise BadRequestError("Required query parameter 'term' not received")

        def to_dict(lab):
            return {
                'value': lab.pk,
                'label': lab.name,
            }

        labs = None
        if query is None:
            labs = Laboratory.objects.all()
        else:
            labs = Laboratory.objects.filter(name__icontains=query)
        return Response(list(map(to_dict, labs)))


class LookupIndex(APIView):
    queryset = Patient.objects.none()

    def get(self, request, registry_code, format=None):
        term = ""
        try:
            term = request.GET['term']
        except KeyError:
            pass
            # raise BadRequestError("Required query parameter 'term' not received")
        registry = Registry.objects.get(code=registry_code)

        if not registry.has_feature('family_linkage'):
            return Response([])

        query = (Q(given_names__icontains=term) | Q(family_name__icontains=term)) & \
            Q(working_groups__in=request.user.working_groups.all(), active=True)

        def to_dict(patient):
            return {
                'pk': patient.pk,
                "class": "Patient",
                'value': patient.pk,
                'label': "%s" % patient,
            }

        return Response(
            list(map(to_dict, [p for p in Patient.objects.filter(query) if p.is_index])))


class CalculatedCdeValue(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, format=None):
        return Response("Use the POST method")

    def post(self, request, format=None):
        # curl -H 'Content-Type: application/json' -X POST -u admin:admin http://localhost:8000/api/v1/calculatedcdes/ -d '{"cde_code":"DDAgeAtDiagnosis", "form_values":{"DateOfDiagnosis":"2019-05-01"},"patient_sex":1, "patient_date_of_birth":"2000-05-17"}'

        patient_values = {'date_of_birth': datetime.strptime(request.data["patient_date_of_birth"], '%Y-%m-%d').date(),
                          'patient_id': request.data["patient_id"],
                          'registry_code': request.data["registry_code"],
                          'sex': str(request.data["patient_sex"])}
        form_values = request.data["form_values"]
        mod = __import__('rdrf.forms.fields.calculated_functions', fromlist=['object'])
        func = getattr(mod, request.data["cde_code"])
        if func:
            return Response(func(patient_values, form_values))
        else:
            raise Exception(f"Trying to call unknown calculated function {request.data['cde_code']}()")


class TaskInfoView(APIView):
    """
    View to get task execution info
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, task_id):
        cae = None
        if task_id is None:
            result = {"status": "error",
                      "message": "Task id not provided"}
        else:
            res = AsyncResult(task_id)
            if res.ready():
                cae = CustomActionExecution.objects.get(task_id=task_id)

                update = cae.status not in ["task finished", "task failed", "task succeeded"]
                if update:
                    cae.status = "task finished"
                    runtime_delta = datetime.now() - cae.created
                    cae.runtime = runtime_delta.seconds
                    cae.save()
                if res.failed():
                    result = {"status": "error",
                              "message": "Task failed"}
                    if update:
                        cae.status = "task failed"
                        runtime_delta = datetime.now() - cae.created
                        cae.runtime = runtime_delta.seconds
                        cae.save()
                elif res.successful():
                    cae.status = "task succeeded"
                    task_result = res.result
                    cae.task_result = json.dumps(task_result)
                    download_link = self._get_download_link(task_id)
                    result = {"status": "completed",
                              "download_link": download_link}
                else:
                    result = {"status": "error",
                              "message": status}
            else:
                result = {"status": "waiting"}

        if cae:
            cae.save()
        return Response(result)

    def _get_download_link(self, task_id):
        return reverse("v1:download-list", args=[task_id])


class TaskResultDownloadView(APIView):
    permission_classes = (IsAuthenticated,)

    def _safe_to_delete(self, filepath):
        """
        Avoid any risk of being hacked somehow
        """
        import os.path
        from django.conf import settings
        dir_ok = filepath.startswith(settings.TASK_FILE_DIRECTORY)
        file_exists = os.path.exists(filepath)
        is_file = os.path.isfile(filepath)
        no_star = "*" not in filepath
        no_dot = "." not in filepath
        no_dollar = "$" not in filepath
        no_semicolon = ";" not in filepath
        no_redirect_input = "<" not in filepath
        no_redirect_output = ">" not in filepath
        return all([dir_ok,
                    no_star,
                    no_dot,
                    file_exists,
                    is_file,
                    no_semicolon,
                    no_redirect_input,
                    no_redirect_output,
                    no_dollar])

    def get(self, request, task_id):
        try:
            res = AsyncResult(task_id)
            cae = CustomActionExecution.objects.get(task_id=task_id)
            cae.status = "predownload"
            cae.save()
            if res.ready() and res.successful():
                import json
                task_result = res.result
                cae.status = "task finished"
                cae.task_result = json.dumps(task_result)
                filepath = task_result.get("filepath", None)
                cae.download_filepath = filepath
                cae.save()
                filename = task_result.get("filename", "download")
                content_type = task_result.get("content_type", None)
                if filepath is not None:
                    if os.path.exists(filepath):
                        with open(filepath, 'rb') as fh:
                            file_data = fh.read()

                        if self._safe_to_delete(filepath):
                            subprocess.run(["rm", filepath], check=True)
                        else:
                            cae.status = "bad download filepath"
                            cae.save()
                            raise Exception("bad filepath")
                        response = HttpResponse(file_data,
                                                content_type=content_type)
                        response['Content-Disposition'] = "inline; filename=%s" % filename
                        cae.status = "downloaded"
                        cae.downloaded_time = datetime.now()
                        cae.save()
                        return response
                    else:
                        # file has already been downloaded
                        message = "The file has already been downloaded"
                        response = HttpResponse(message,
                                                content_type="application/text")
                        response['Content-Disposition'] = "inline; filename=%s" % "error.txt"
                        return response

        except Exception as ex:
            logger.error("Error getting task download: %s" % ex)
            raise Exception("Server Error getting download")
