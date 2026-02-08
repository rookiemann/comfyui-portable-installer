"""Collect and register all API route modules."""
from api.routes.status import setup as setup_status
from api.routes.install import setup as setup_install
from api.routes.comfyui import setup as setup_comfyui
from api.routes.instances import setup as setup_instances
from api.routes.models import setup as setup_models
from api.routes.nodes import setup as setup_nodes
from api.routes.jobs_routes import setup as setup_jobs
from api.routes.logs import setup as setup_logs


def setup_routes(app):
    """Register all route modules with the app."""
    setup_status(app)
    setup_install(app)
    setup_comfyui(app)
    setup_instances(app)
    setup_models(app)
    setup_nodes(app)
    setup_jobs(app)
    setup_logs(app)
