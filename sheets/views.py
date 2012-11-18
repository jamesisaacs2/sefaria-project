from django.template import Context, loader, RequestContext
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from django.contrib.auth.models import User, Group
from sefaria.texts import *
from sefaria.sheets import *
from sefaria.util import *


@ensure_csrf_cookie
def new_sheet(request):
	viewer_groups = request.user.groups.all() if request.user.is_authenticated() else None
	return render_to_response('sheets.html', {"can_edit": True,
												"new_sheet": True,
												"viewer_groups": viewer_groups,
												"owner_groups": viewer_groups,
											    "current_url": request.get_full_path,
											    "toc": get_toc(), },
											     RequestContext(request))


@ensure_csrf_cookie
def view_sheet(request, sheet_id):
	sheet = get_sheet(sheet_id)
	if "error" in sheet:
		return HttpResponse(sheet["error"])
	can_edit = sheet["owner"] == request.user.id or sheet["status"] in EDITABLE_SHEETS
	try:
		owner = User.objects.get(id=sheet["owner"])
		author = owner.first_name + " " + owner.last_name
		owner_groups = owner.groups.all() if sheet["owner"] == request.user.id else None
	except User.DoesNotExist:
		author = "Someone Mysterious"
		owner_groups = None
	sheet_group = sheet["group"].replace(" ", "-") if sheet["status"] == PARTNER_SHEET else None
	viewer_groups = request.user.groups.all() if request.user.is_authenticated() else None
	return render_to_response('sheets.html', {"sheetJSON": json.dumps(sheet), 
												"can_edit": can_edit, 
												"title": sheet["title"],
												"author": author,
												"owner_groups": owner_groups,
												"sheet_group":  sheet_group,
												"viewer_groups": viewer_groups,
												"current_url": request.get_full_path,
												"toc": get_toc(),},
												 RequestContext(request))

@ensure_csrf_cookie
def topic_view(request, topic):
	sheet = get_topic(topic)
	if "error" in sheet:
		return HttpResponse(sheet["error"])
	can_edit = request.user.is_authenticated()
	try:
		owner = User.objects.get(id=sheet["owner"])
		author = owner.first_name + " " + owner.last_name
	except User.DoesNotExist:
		author = "Someone Mysterious"
	return render_to_response('sheets.html', {"sheetJSON": json.dumps(sheet), 
												"can_edit": can_edit, 
												"title": sheet["title"],
												"author": author,
												"topic": True,
												"current_url": request.get_full_path,
												"toc": get_toc(),},
												 RequestContext(request))


def topics_list(request):
	# Show index of all topics
	topics = db.sheets.find({"status": 5}).sort([["title", 1]])
	return render_to_response('topics.html', {"topics": topics,
												"status": 5,
												"group": "topics",
												"title": "Torah Sources by Topic",
												"toc": get_toc(),},
												 RequestContext(request))	


def partner_page(request, partner):
	# Show Partner Page 
	if not request.user.is_authenticated():
		return redirect("login")

	try:
		group = Group.objects.get(name=partner)
	except Group.DoesNotExist:
		group = None
	if group not in request.user.groups.all():
		return redirect("home")

	topics = db.sheets.find({"status": 6, "group": partner}).sort([["title", 1]])
	return render_to_response('topics.html', {"topics": topics,
												"status": 6,
												"group": partner,
												"title": "%s's Topics" % partner,
												"toc": get_toc(),},
												 RequestContext(request))	


def sheet_list_api(request):
	# Show list of available sheets
	if request.method == "GET":
		return jsonResponse(sheet_list())

	# Save a sheet
	if request.method == "POST":
		if not request.user.is_authenticated():
			return jsonResponse({"error": "You must be logged in to save."})
		
		j = request.POST.get("json")
		if not j:
			return jsonResponse({"error": "No JSON given in post data."})
		sheet = json.loads(j)
		if "id" in sheet:
			existing = get_sheet(sheet["id"])
			if existing["owner"] != request.user.id and not existing["status"] in (LINK_SHEET_EDIT, PUBLIC_SHEET_EDIT):
				return jsonResponse({"error": "You don't have permission to edit this sheet."})
		
		return jsonResponse(save_sheet(sheet, request.user.id))


def user_sheet_list_api(request, user_id):
	if int(user_id) != request.user.id:
		return jsonResponse({"error": "You are not authorized to view that."})
	return jsonResponse(sheet_list(user_id))


def sheet_api(request, sheet_id):
	if request.method == "GET":
		sheet = get_sheet(int(sheet_id))
		can_edit = sheet["owner"] == request.user.id or sheet["status"] in (PUBLIC_SHEET_VIEW, PUBLIC_SHEET_EDIT)
		return jsonResponse(sheet, {"can_edit": can_edit})

	if request.method == "POST":
		return jsonResponse({"error": "TODO - save to sheet by id"})


def add_to_sheet_api(request, sheet_id):
	ref = request.POST.get("ref")
	if not ref:
		return jsonResponse({"error": "No ref given in post data."})
	return jsonResponse(add_to_sheet(int(sheet_id), ref))
