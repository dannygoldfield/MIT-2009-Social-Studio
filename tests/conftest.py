import pytest

from mit2009_studio.demo import make_sources
from mit2009_studio.models import NewProject
from mit2009_studio.service import Studio


@pytest.fixture
def studio(tmp_path):
    return Studio(tmp_path / "data")


@pytest.fixture
def project(studio):
    return studio.create_project(NewProject(name="Test story", author="Test author"))


@pytest.fixture
def source_assets(studio, project, tmp_path):
    audio, photos = make_sources(tmp_path / "fixtures")
    return [studio.add_asset(project["id"], "reference", audio.name, audio)] + [
        studio.add_asset(project["id"], "photo", p.name, p) for p in photos
    ]
