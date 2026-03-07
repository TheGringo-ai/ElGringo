"""Tests for projects_service — project discovery, GitHub API, tech stack detection."""

from unittest.mock import patch

from products.fred_assistant.services import projects_service


# ── detect_tech_stack ─────────────────────────────────────────────

def test_detect_tech_stack_python(tmp_path):
    (tmp_path / "requirements.txt").touch()
    (tmp_path / "pyproject.toml").touch()
    stack = projects_service.detect_tech_stack(str(tmp_path))
    assert "Python" in stack


def test_detect_tech_stack_node(tmp_path):
    (tmp_path / "package.json").touch()
    stack = projects_service.detect_tech_stack(str(tmp_path))
    assert "Node.js" in stack


def test_detect_tech_stack_docker(tmp_path):
    (tmp_path / "Dockerfile").touch()
    (tmp_path / "docker-compose.yml").touch()
    stack = projects_service.detect_tech_stack(str(tmp_path))
    assert "Docker" in stack


def test_detect_tech_stack_react_from_src(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "App.jsx").touch()
    stack = projects_service.detect_tech_stack(str(tmp_path))
    assert "React" in stack


def test_detect_tech_stack_empty_dir(tmp_path):
    assert projects_service.detect_tech_stack(str(tmp_path)) == []


def test_detect_tech_stack_nonexistent():
    assert projects_service.detect_tech_stack("/nonexistent/path") == []


# ── get_project_info (non-git) ───────────────────────────────────

def test_get_project_info_non_git(tmp_path):
    (tmp_path / "main.py").touch()
    info = projects_service.get_project_info(str(tmp_path))
    assert info["name"] == tmp_path.name
    assert info["is_git"] is False
    assert info["git_branch"] is None
    assert info["path"] == str(tmp_path)


def test_get_project_info_with_tech_stack(tmp_path):
    (tmp_path / "package.json").touch()
    (tmp_path / "tsconfig.json").touch()
    info = projects_service.get_project_info(str(tmp_path))
    assert "Node.js" in info["tech_stack"]
    assert "TypeScript" in info["tech_stack"]


# ── _is_git_repo ─────────────────────────────────────────────────

def test_is_git_repo_false(tmp_path):
    assert projects_service._is_git_repo(str(tmp_path)) is False


def test_is_git_repo_true(tmp_path):
    (tmp_path / ".git").mkdir()
    assert projects_service._is_git_repo(str(tmp_path)) is True


# ── _gh_repo_to_project ──────────────────────────────────────────

def test_gh_repo_to_project():
    repo = {
        "name": "my-repo",
        "language": "Python",
        "default_branch": "main",
        "pushed_at": "2026-02-20T10:00:00Z",
        "clone_url": "https://github.com/user/my-repo.git",
        "description": "A test repo",
        "private": True,
        "stargazers_count": 5,
        "open_issues_count": 2,
    }
    project = projects_service._gh_repo_to_project(repo)
    assert project["name"] == "my-repo"
    assert project["is_git"] is True
    assert project["git_branch"] == "main"
    assert "Python" in project["tech_stack"]
    assert project["private"] is True
    assert project["stars"] == 5
    assert project["source"] == "github"


def test_gh_repo_to_project_no_language():
    repo = {"name": "bare-repo", "clone_url": "https://github.com/user/bare.git"}
    project = projects_service._gh_repo_to_project(repo)
    assert project["tech_stack"] == []


# ── list_projects (local only, no GitHub) ────────────────────────

def test_list_projects_local_dirs(tmp_path):
    (tmp_path / "project_a").mkdir()
    (tmp_path / "project_b").mkdir()
    (tmp_path / ".hidden").mkdir()  # should be skipped

    with patch.object(projects_service, "PROJECTS_DIR", str(tmp_path)), \
         patch.object(projects_service, "CLONE_DIR", str(tmp_path / "clones")), \
         patch.object(projects_service, "GITHUB_TOKEN", ""):
        projects = projects_service.list_projects(str(tmp_path))
    names = [p["name"] for p in projects]
    assert "project_a" in names
    assert "project_b" in names
    assert ".hidden" not in names


def test_list_projects_empty_dir(tmp_path):
    with patch.object(projects_service, "PROJECTS_DIR", str(tmp_path)), \
         patch.object(projects_service, "CLONE_DIR", str(tmp_path / "clones")), \
         patch.object(projects_service, "GITHUB_TOKEN", ""):
        projects = projects_service.list_projects(str(tmp_path))
    assert projects == []


# ── list_projects with GitHub (mocked) ───────────────────────────

def test_list_projects_merges_github_repos(tmp_path):
    (tmp_path / "local_proj").mkdir()

    mock_repos = [
        {"name": "remote_only", "language": "Python", "clone_url": "https://github.com/user/remote_only.git",
         "fork": False, "default_branch": "main", "pushed_at": "2026-02-20T00:00:00Z"},
        {"name": "local_proj", "language": "Python", "clone_url": "https://github.com/user/local_proj.git",
         "fork": False, "default_branch": "main", "pushed_at": "2026-02-20T00:00:00Z"},
    ]

    with patch.object(projects_service, "PROJECTS_DIR", str(tmp_path)), \
         patch.object(projects_service, "CLONE_DIR", str(tmp_path / "clones")), \
         patch.object(projects_service, "GITHUB_TOKEN", "fake-token"), \
         patch.object(projects_service, "_fetch_github_repos", return_value=mock_repos):
        projects = projects_service.list_projects(str(tmp_path))

    names = [p["name"] for p in projects]
    assert "local_proj" in names
    assert "remote_only" in names
    # No duplicates
    assert names.count("local_proj") == 1


def test_list_projects_skips_forks(tmp_path):
    mock_repos = [
        {"name": "forked_repo", "language": "JS", "clone_url": "https://github.com/user/fork.git",
         "fork": True, "default_branch": "main"},
    ]

    with patch.object(projects_service, "PROJECTS_DIR", str(tmp_path)), \
         patch.object(projects_service, "CLONE_DIR", str(tmp_path / "clones")), \
         patch.object(projects_service, "GITHUB_TOKEN", "fake-token"), \
         patch.object(projects_service, "_fetch_github_repos", return_value=mock_repos):
        projects = projects_service.list_projects(str(tmp_path))

    names = [p["name"] for p in projects]
    assert "forked_repo" not in names


# ── get_project ──────────────────────────────────────────────────

def test_get_project_local(tmp_path):
    (tmp_path / "my_project").mkdir()
    with patch.object(projects_service, "PROJECTS_DIR", str(tmp_path)), \
         patch.object(projects_service, "CLONE_DIR", str(tmp_path / "clones")):
        project = projects_service.get_project("my_project")
    assert project is not None
    assert project["name"] == "my_project"


def test_get_project_not_found(tmp_path):
    with patch.object(projects_service, "PROJECTS_DIR", str(tmp_path)), \
         patch.object(projects_service, "CLONE_DIR", str(tmp_path / "clones")), \
         patch.object(projects_service, "GITHUB_TOKEN", ""):
        project = projects_service.get_project("nonexistent_project")
    assert project is None


# ── _fetch_github_repos cache ────────────────────────────────────

def test_fetch_github_repos_uses_cache():
    mock_data = [{"name": "cached_repo"}]
    projects_service._gh_cache = mock_data
    projects_service._gh_cache_time = __import__("time").time()  # fresh

    result = projects_service._fetch_github_repos()
    assert result == mock_data

    # Clean up
    projects_service._gh_cache = []
    projects_service._gh_cache_time = 0


def test_fetch_github_repos_expired_cache():
    projects_service._gh_cache = [{"name": "old"}]
    projects_service._gh_cache_time = 0  # epoch = expired

    with patch.object(projects_service, "_gh_api", return_value=None), \
         patch.object(projects_service, "GITHUB_TOKEN", ""), \
         patch.object(projects_service, "GITHUB_ORG", ""):
        result = projects_service._fetch_github_repos()

    # No token → returns empty
    assert result == []

    # Clean up
    projects_service._gh_cache = []
    projects_service._gh_cache_time = 0
