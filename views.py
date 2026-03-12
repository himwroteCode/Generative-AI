# laptop_guide/views.py
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .service import get_laptop_answer


def guide_page(request):
    """Render the laptop buying guide page (Learn + Q&A chat)."""
    return render(request, "laptop_guide/guide.html")


@csrf_exempt
@require_http_methods(["GET", "POST"])
def guide_laptop_query(request):
    """Handle chat requests for laptop Q&A and recommendations."""
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:
        data = request.GET

    query = data.get("q") or data.get("message") or ""
    if not query.strip():
        return JsonResponse({"answer": "Please type a question about laptops or describe what you need."}, status=400)

    try:
        answer = get_laptop_answer(query)
    except Exception as e:
        return JsonResponse({"answer": f"Error: {str(e)}"}, status=500)

    return JsonResponse({"answer": answer})
