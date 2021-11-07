{{fullname | escape | underline}}

.. automodule:: {{fullname}}
    :show-inheritance:
    :member-order: bysource
    :members:
    :undoc-members:

{% block modules %}
{% if modules %}
.. rubric:: Modules

.. autosummary::
    :toctree:
    :recursive:
    :nosignatures:

    {% for item in modules %}
    ~{{item}}
    {% endfor %}
{% endif %}
{% endblock %}
