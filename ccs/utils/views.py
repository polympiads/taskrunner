
import json
from typing import Any, Callable, Dict, Generic, List, Tuple, TypeVar

from django.http import HttpRequest, JsonResponse
from django.views import View

from django.db import models

from ccs.utils.responses import Json400, Json403
from asgiref.sync import sync_to_async

T = TypeVar("T")

class UpdateField:
    source      : str
    destination : str

    validator : "Callable[[Any], Tuple[Any | None, str | None]]"

    def __init__ (
            self,
            source: str,
            destination: "str | None" = None,
            validator: "Callable[[Any], Tuple[Any | None, str | None]]" = lambda x: (x, None)
        ):
        self.source      = source
        self.destination = destination if destination is not None else source
        self.validator   = validator

class CollectionView (Generic[T], View):
    view_rule   : str | None = None
    create_rule : str | None = None

    model : models.Model = None

    async def get_queryset (self, request: HttpRequest, *args, **kwargs) -> "models.QuerySet[models.Model, models.Model]":
        raise NotImplementedError()
    async def display_json (self, item: T) -> Any:
        raise NotImplementedError()
    def get_fields (self) -> List[UpdateField]:
        raise NotImplementedError()
    
    async def create (self, updates: Dict, request: HttpRequest, *args, **kwargs):
        raise NotImplementedError()
    
    async def post (self, request: HttpRequest, *args, **kwargs):
        assert self.create_rule is not None, "Please provide the create rule"
        
        user = await request.auser()
        if not await user.ahas_perm(self.create_rule):
            return Json403("Missing permissions")
        
        try:
            content = json.loads(request.body.decode('utf-8'))
            assert isinstance(content, dict)
        except Exception:
            return Json400("Malformed JSON body")

        updates = {}
        for field in self.get_fields():
            payload = content.get(field.source)
            target, message = field.validator(payload)
            
            if message is not None:
                return Json400(message.format(field = field.source))
            if target is None:
                continue

            updates[field.destination] = target

        result = await self.create(updates, request, *args, **kwargs)
        if isinstance(result, JsonResponse):
            return result
        
        created_item, location = result

        response = JsonResponse(await self.display_json(created_item))
        response.headers['Location'] = location
        
        return response

    async def get (self, request: HttpRequest, *args, **kwargs):
        assert self.view_rule is not None, "Please provide the view rule"
        collection = await self.get_queryset(request, *args, **kwargs)

        user = await request.auser()
        
        def filtered_items ():
            filtered = []

            for item in collection:
                if user.has_perm(self.view_rule, item):
                    filtered.append(item)

            return filtered
        
        result = []
        
        items = await sync_to_async(filtered_items)()
        for item in items:
            result.append(
                await self.display_json(item)
            )

        return JsonResponse(result, safe = False)
