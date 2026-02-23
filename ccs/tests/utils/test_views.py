
import asyncio

from django.test import TestCase

from ccs.utils.views import CollectionView


class TestCollectionView (TestCase):
    def test_failures (self):
        view = CollectionView()

        with self.assertRaises(NotImplementedError):
            view.get_fields()
        with self.assertRaises(NotImplementedError):
            asyncio.run( view.get_queryset(None) )
        with self.assertRaises(NotImplementedError):
            asyncio.run( view.display_json(None) )
        with self.assertRaises(NotImplementedError):
            asyncio.run( view.create({}, None) )
