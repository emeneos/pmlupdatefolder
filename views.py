from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import Measure
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.contrib.staticfiles import finders  # Required for static files in PDF
from django.db.models import Q

def index(request):
    #   measures = Measure.objects.all()
    return render(request, 'app/index.html', {'measures': Measure.objects.none()})

def filter_measures(request):
    search_term = request.GET.get('search', '').strip()
    data = []

    try:
        if search_term:
            query = Q()
            for word in search_term.split():
                query |= (
                    Q(author_list__icontains=word) |
                    Q(acronym__icontains=word) |
                    Q(name__icontains=word) |
                    Q(keywords__icontains=word) |
                    Q(journal__icontains=word)
                )
            measures = Measure.objects.filter(query).distinct()
        else:
            measures = Measure.objects.none()

        data = [{
            'acronym': m.acronym,
            'name': m.name,
            'author_list': m.author_list,
            'journal': m.journal,
            'keywords': m.keywords,
            'measure_type': m.get_measure_type_display(),
            'who_completes': m.get_who_completes_display(),
            'id': m.id
        } for m in measures]

    except Exception as e:
        print(f"Error in filter_measures: {str(e)}")  # Check console for errors
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse(data, safe=False)


def link_callback(uri, rel):
    """
    Proper static file resolver for PDF generation
    """
    if uri.startswith('/static/'):
        # Use Django's staticfiles finders to resolve the path
        path = finders.find(uri.replace('/static/', '', 1))
        if path:
            return path
    # Fallback for other URIs (external URLs, data URIs, etc.)
    return uri

def generate_pdf(request, report_type):
    measure_ids = request.GET.get('ids', '').split(',')
    measures = Measure.objects.filter(id__in=measure_ids)
    
    template = 'app/report_full.html' if report_type == 'full' else 'app/report_list.html'
    html = render_to_string(template, {'measures': measures})
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="{report_type}_report.pdf"'
    
    # Create PDF with proper static file handling
    pisa_status = pisa.CreatePDF(
        html,
        dest=response,
        encoding='UTF-8',
        link_callback=link_callback  # Use the proper callback
    )
    
    if pisa_status.err:
        return HttpResponse('PDF generation error')
    return response