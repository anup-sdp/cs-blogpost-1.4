// to be used in templates/post.html
// handles edit and delete post functionality
/* 
this file was previously inline in templates/post.html, note: External JS cannot contain Jinja2 syntax, eg. "{{ post.id }}"
Get post ID from Jinja2 template
*/

// import {getErrorMessage, hideModal, showModal,} from "/static/js/utils.js"; // absolute path from site/domain root
import { getCurrentUser, getToken } from '/static/js/auth.js';
import { getErrorMessage, showModal, hideModal } from '/static/js/utils.js';

// Get post ID from the hidden input field
const postId = Number(document.querySelector('input[name="post_id"]').value);
const postUserId = Number(document.querySelector('.content-section').dataset.userId); // get user_id from data attribute on article element

// Show edit/delete buttons only if current user owns this post
async function checkOwnership() {
    const user = await getCurrentUser();
    if (user && user.id === postUserId) {
        document.getElementById('postActions').classList.remove('d-none');
    }
}

// Edit Post Form Handler
const editForm = document.getElementById('editPostForm');
editForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const token = getToken();
    if (!token) { window.location.href = '/login'; return; }
    const formData = new FormData(editForm);
    const postData = Object.fromEntries(formData.entries());
    // Remove post_id from data (it's in the URL, not the body)
    delete postData.post_id;
    try {
        const response = await fetch(`/api/posts/${postId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify(postData),
        });
        if (response.status === 401) { window.location.href = '/login'; return; }
        if (response.status === 403) {
            document.getElementById('errorMessage').textContent = 'You are not authorized to edit this post.';
            hideModal('editModal');
            showModal('errorModal');
            return;
        }
        if (response.ok) {
            document.getElementById('successMessage').textContent = 'Post updated successfully!';
            hideModal('editModal');
            showModal('successModal');
            document.getElementById('successModal').addEventListener('hidden.bs.modal', () => {
                window.location.reload();
            }, { once: true });
        } else {
            const error = await response.json();
            document.getElementById('errorMessage').textContent = getErrorMessage(error);
            hideModal('editModal');
            showModal('errorModal');
        }
    } catch (error) {
        document.getElementById('errorMessage').textContent =
            'Network error. Please check your connection and try again.';
        showModal('errorModal');
    }      
});

// Delete Post Handler
const deleteButton = document.getElementById('confirmDelete');
deleteButton.addEventListener('click', async () => {
    const token = getToken();
    if (!token) { window.location.href = '/login'; return; }
    try {
        const response = await fetch(`/api/posts/${postId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (response.status === 401) { window.location.href = '/login'; return; }
        if (response.status === 403) {
            document.getElementById('errorMessage').textContent = 'You are not authorized to delete this post.';
            hideModal('deleteModal');
            showModal('errorModal');
            return;
        }
        if (response.status === 204) {
            window.location.href = '/';
        } else {
            const error = await response.json();
            document.getElementById('errorMessage').textContent = getErrorMessage(error);
            hideModal('deleteModal');
            showModal('errorModal');
        }
    } catch (error) {
        document.getElementById('errorMessage').textContent = 'Network error. Please check your connection and try again.';
        showModal('errorModal');
    }
});
checkOwnership();


/*
HTML Dataset API, it's an automatic conversion between data attributes and JS properties.
For example, an element like this:  
<div id="myElement" data-user-id="123" data-user-name="Alice"></div>
Can be accessed in JavaScript like this:
const myElement = document.getElementById('myElement');
const userId = myElement.dataset.userId; // "123" (string)
const userName = myElement.dataset.userName; // "Alice" (string)
*/


/*
alternate solutioon:
in html,
{% block scripts %}
    <script>
        // Declare global variable in template (processed by Jinja2)
        window.postId = {{ post.id }};
    </script>
    <script type="module" src="{{ url_for('static', path='js/post.js') }}"></script>
{% endblock scripts %}

// Use the global variable in external js (no template syntax here)
const postId = window.postId;
*/

// if the bootstrap modal closed, shows console error, 
// described here: https://stackoverflow.com/questions/79571480/getting-error-in-browser-console-after-closing-bootstrap-modal