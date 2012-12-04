import ml_grading_util
from django.forms.models import model_to_dict

_INTERFACE_VERSION=1

def request_latest_created_model(request):
    if request.type!="GET":
        return util._error_response("This must use HTTP GET", _INTERFACE_VERSION)

    request_data=request.GET
    if not request_data.has_key("location"):
        return util._error_response("Need to include key location", _INTERFACE_VERSION)

    success, model=get_latest_created_model(request_data['location'])

    if not success:
        return util._error_response("Could not get model: {0}".format(model), _INTERFACE_VERSION)

    model_dict=model_to_dict(model, fields=[field.name for field in model._meta.fields])

    return util.success_message({'model' : model}, _INTERFACE_VERSION)



