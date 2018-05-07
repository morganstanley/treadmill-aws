"""Treadmill AWS Image REST api.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import flask
import flask_restplus as restplus
from flask_restplus import fields

from treadmill import webutils


def init(api, cors, impl):
    """Configures REST handlers for AWS image resource."""

    namespace = webutils.namespace(
        api, __name__, 'AWS Image REST operations'
    )

    model = {
        'ImageId': fields.String(description='Image id.'),
        'Name': fields.String(description='Image name.'),
        'OwnerId': fields.String(description='Image account.'),
        'CreationDate': fields.String(description='Date created.'),
        'State': fields.String(description='State.'),
    }

    aws_image_model = api.model(
        'AWSImage', model
    )

    match_parser = api.parser()
    match_parser.add_argument('account', help='Image account',
                              location='args', required=False,)

    @namespace.route(
        '/',
    )
    class _ImageResourceList(restplus.Resource):
        """Treadmill App monitor resource"""

        @webutils.get_api(api, cors,
                          marshal=api.marshal_list_with,
                          resp_model=aws_image_model,
                          parser=match_parser)
        def get(self):
            """Returns list of configured app monitors."""
            return impl.list()

    @namespace.route('/<image>')
    @api.doc(params={'image': 'Image name'})
    class _ImageResource(restplus.Resource):
        """Treadmill AWS Image resource."""

        @webutils.get_api(api, cors,
                          marshal=api.marshal_with,
                          resp_model=aws_image_model)
        def get(self, image):
            """Return Treadmill application monitor configuration."""
            return impl.get(image)

        @webutils.post_api(api, cors,
                           req_model=aws_image_model,
                           resp_model=aws_image_model)
        def post(self, app_monitor):
            """Creates AWS image."""
            return impl.create(app_monitor, flask.request.json)

        @webutils.put_api(api, cors,
                          req_model=aws_image_model,
                          resp_model=aws_image_model)
        def put(self, image):
            """Updates Treadmill application configuration."""
            return impl.update(image, flask.request.json)

        @webutils.delete_api(api, cors)
        def delete(self, image):
            """Deletes Treadmill application monitor."""
            return impl.delete(image)
