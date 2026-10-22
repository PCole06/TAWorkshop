import pytest

import app as task_app


@pytest.fixture
def client():
    """Provide a Flask test client."""
    task_app.app.config['TESTING'] = True
    with task_app.app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def reset_tasks():
    """Reset tasks and the next task identifier before each test."""
    task_app.tasks.clear()
    task_app.tasks.extend([
        {"id": 1, "title": "Project-1 Report"},
        {"id": 2, "title": "Project-2 MMFs"}
    ])
    task_app.next_id = 3


def test_index(client):
    """Render the task tracker page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Task Tracker" in response.data


def test_get_tasks(client):
    """Return existing tasks with the default priority."""
    response = client.get('/api/tasks')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert [task['priority'] for task in data] == ['Medium', 'Medium']


def test_existing_task_without_priority_defaults_to_medium(client):
    """Normalize stored tasks that do not contain a priority."""
    task_app.tasks.append({"id": 3, "title": "Stored task"})

    response = client.get('/api/tasks')

    assert response.status_code == 200
    stored_task = response.get_json()[-1]
    assert stored_task['priority'] == 'Medium'


def test_malformed_stored_priority_defaults_to_medium(client):
    """Normalize unhashable priorities loaded from storage."""
    task_app.tasks.extend([
        {"id": 3, "title": "List priority", "priority": []},
        {"id": 4, "title": "Object priority", "priority": {}}
    ])

    response = client.get('/api/tasks')

    assert response.status_code == 200
    priorities = [task['priority'] for task in response.get_json()]
    assert priorities[-2:] == ['Medium', 'Medium']


@pytest.mark.parametrize('priority', ['Low', 'Medium', 'High'])
def test_add_task_accepts_supported_priorities(client, priority):
    """Create tasks with each supported priority."""
    response = client.post(
        '/api/tasks',
        json={"title": f"{priority} task", "priority": priority}
    )

    assert response.status_code == 201
    assert response.get_json()['priority'] == priority


def test_add_task_defaults_missing_priority_to_medium(client):
    """Default a task priority when the request omits it."""
    response = client.post('/api/tasks', json={"title": "Default task"})

    assert response.status_code == 201
    assert response.get_json()['priority'] == 'Medium'


@pytest.mark.parametrize('priority', ['', 'Urgent', None, 123, [], {}])
def test_add_task_defaults_invalid_priority_to_medium(client, priority):
    """Default unsupported task priorities to Medium."""
    response = client.post(
        '/api/tasks',
        json={"title": "Invalid priority task", "priority": priority}
    )

    assert response.status_code == 201
    assert response.get_json()['priority'] == 'Medium'


def test_get_tasks_returns_created_priority(client):
    """Return a created task's priority from the tasks endpoint."""
    client.post(
        '/api/tasks',
        json={"title": "High priority task", "priority": "High"}
    )

    response = client.get('/api/tasks')

    assert response.status_code == 200
    created_task = response.get_json()[-1]
    assert created_task['priority'] == 'High'


def test_add_task_success(client):
    """Create a task while preserving the existing creation behavior."""
    response = client.post('/api/tasks', json={"title": "Test new task"})
    assert response.status_code == 201
    assert response.get_json()['title'] == "Test new task"
    get_response = client.get('/api/tasks')
    assert len(get_response.get_json()) == 3


def test_add_task_missing_title(client):
    """Reject task creation requests without a title."""
    response = client.post('/api/tasks', json={"wrong_key": "value"})
    assert response.status_code == 400
    assert "error" in response.get_json()
    response2 = client.post('/api/tasks', json={})
    assert response2.status_code == 400


def test_delete_task(client):
    """Delete an existing task."""
    response = client.delete('/api/tasks/1')
    assert response.status_code == 200
    get_response = client.get('/api/tasks')
    data = get_response.get_json()
    assert len(data) == 1
    assert data[0]['id'] == 2
