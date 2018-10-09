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
        api, 'aws-image', 'AWS Image REST operations'
    )

    # TODO: will it make sense to maintain models in separate module?
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

    aws_image_create_model = api.model('AWSCreateImage', {
        'instance': fields.String(
            description='Instance ID of the image building instance.'
        )
    })

    resource_fields = {
        'tags': fields.Raw(description='Tags k/v dictionary'),
        'name': fields.String(description='Resource name'),
        'ids': fields.List(fields.String, description='List of resource ids')
    }

    aws_image_req_model = api.model('AWSImageRequest', {
        'base_image': fields.Nested(resource_fields, description='Base image'),
        'base_image_account': fields.String(description='Base image account.'),
        'userdata': fields.List(fields.String, description='User data.'),
        'profile': fields.String(description='Instance profile.'),
        'secgroup': fields.Nested(resource_fields, description='AWS secgroup'),
        'subnet': fields.Nested(resource_fields, description='AWS subnet'),
        'key': fields.String(description='Instance ssh key.'),
    })

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
                           req_model=aws_image_req_model,
                           resp_model=aws_image_create_model)
        def post(self, image):
            """Creates AWS image."""
            return impl.create(image, flask.request.json)

        @webutils.delete_api(api, cors)
        def delete(self, image):
            """Deletes AWS image."""
            return impl.delete(image)
