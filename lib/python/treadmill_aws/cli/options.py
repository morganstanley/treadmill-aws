"""Helpers to construct options handler for AWS resources."""

import collections
import functools

import click


def _opt_tag(resource, opt_handler_clbk):
    """Return tag option."""
    return click.option(
        '--{}-tag'.format(resource),
        required=False,
        expose_value=False,
        type=(str, str),
        callback=opt_handler_clbk,
        multiple=True,
        help='{} tag.'.format(resource.capitalize())
    )


def _opt(resource, attr, opt_handler_clbk):
    """Return resource option for given tag/attribute."""
    return click.option(
        '--{}-{}'.format(resource, attr),
        required=False,
        expose_value=False,
        callback=opt_handler_clbk,
        help='{} {}.'.format(resource.capitalize(), attr)
    )


def _init_arg(arg):
    """Initialize argument with defaults."""
    assert isinstance(arg, dict), 'Invalid parameter type, expect dict.'
    if 'id' not in arg:
        arg['id'] = None
    if 'tags' not in arg:
        arg['tags'] = collections.defaultdict(list)


def _make_opt_handler(arg, resource, attrs=None, special_tags=None):
    """Make option handler for given resource."""

    if special_tags is None:
        special_tags = ['Name']

    if attrs is None:
        attrs = ['id']

    def _handle_context_opt(ctx, param, value):
        """Handle subnet options."""
        if not value or ctx.resilient_parsing:
            return

        if value == '-':
            return

        _init_arg(arg)

        opt = param.name
        if opt == '{}_tag'.format(resource):
            for tag_name, tag_value in value:
                arg['tags'][tag_name].append(tag_value)

        for attr in attrs:
            if opt == '{}_{}'.format(resource.lower(), attr.lower()):
                arg[attr] = value

        for tag in special_tags:
            if opt == '{}_{}'.format(resource.lower(), tag.lower()):
                arg['tags'][tag].append(value)

    return _handle_context_opt


def make_subnet_opts(arg):
    """Make subnet CLI options decorator."""

    opt_handler_clbk = _make_opt_handler(arg, 'subnet')

    def decorated(func):
        """Decorator which adds subnet CLI options."""

        @_opt('subnet', 'id', opt_handler_clbk)
        @_opt('subnet', 'name', opt_handler_clbk)
        @_opt_tag('subnet', opt_handler_clbk)
        def wrapped_function(*args, **kwargs):
            """CLI handler."""
            return func(*args, **kwargs)

        func.provide_automatic_options = False
        return functools.update_wrapper(wrapped_function, func)

    return decorated


def make_secgroup_opts(arg):
    """Make security group CLI options decorator."""

    opt_handler_clbk = _make_opt_handler(arg, 'secgroup')

    def decorated(func):
        """Decorator which adds subnet CLI options."""

        @_opt('secgroup', 'id', opt_handler_clbk)
        @_opt('secgroup', 'name', opt_handler_clbk)
        @_opt_tag('secgroup', opt_handler_clbk)
        def wrapped_function(*args, **kwargs):
            """CLI handler."""
            return func(*args, **kwargs)

        func.provide_automatic_options = False
        return functools.update_wrapper(wrapped_function, func)

    return decorated


def make_image_opts(arg):
    """Make image CLI options decorator."""

    opt_handler_clbk = _make_opt_handler(
        arg, 'image', attrs=['id', 'name', 'owner'], special_tags=[]
    )

    def decorated(func):
        """Decorator which adds image CLI options."""

        @_opt('image', 'id', opt_handler_clbk)
        @_opt('image', 'name', opt_handler_clbk)
        @_opt('image', 'owner', opt_handler_clbk)
        @_opt_tag('image', opt_handler_clbk)
        def wrapped_function(*args, **kwargs):
            """CLI handler."""
            return func(*args, **kwargs)

        func.provide_automatic_options = False
        return functools.update_wrapper(wrapped_function, func)

    return decorated
