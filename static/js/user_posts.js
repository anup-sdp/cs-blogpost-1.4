//  to be used in templates/user_posts.html

import { escapeHtml, formatDate } from '/static/js/utils.js';

//   const userId = {{ user.id }};
//   let currentOffset = {{ limit }};
//   const limit = {{ limit }};
//   let hasMore = {{ 'true' if has_more else 'false' }};

  const postsContainer = document.getElementById('postsContainer');
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const userId = Number(postsContainer.dataset.userId);
  let currentOffset = Number(postsContainer.dataset.limit);  
  let hasMore = JSON.parse(postsContainer.dataset.hasMore); // let hasMore = postsContainer.dataset.hasMore === 'true';

  function createPostHTML(post) {
    return `
      <article class="content-section py-3 px-4 mb-4">
        <div class="d-flex align-items-start gap-4">
          <img class="rounded-circle article-img flex-shrink-0" src="${escapeHtml(post.author.image_path)}" alt="${escapeHtml(post.author.username)}'s profile picture" width="64" height="64" loading="lazy">
          <div class="flex-grow-1">
            <div class="article-metadata mb-2">
              <a class="me-2" href="/users/${post.author.id}/posts">${escapeHtml(post.author.username)}</a>
              <small class="text-body-secondary">${formatDate(post.date_posted)}</small>
            </div>
            <h2>
              <a class="article-title" href="/posts/${post.id}">${escapeHtml(post.title)}</a>
            </h2>
            <p class="article-content">${escapeHtml(post.content)}</p>
          </div>
        </div>
      </article>
    `;
  }

  async function loadMorePosts() {
    loadMoreBtn.disabled = true;
    loadMoreBtn.textContent = 'Loading...';

    let errorOccurred = false;

    try {
      const response = await fetch(`/api/users/${userId}/posts?skip=${currentOffset}&limit=${limit}`);

      if (!response.ok) {
        throw new Error('Failed to fetch posts');
      }

      const data = await response.json();

      for (const post of data.posts) {
        postsContainer.insertAdjacentHTML('beforeend', createPostHTML(post));
      }

      currentOffset += data.posts.length;
      hasMore = data.has_more;

      if (!hasMore) {
        loadMoreBtn.classList.add('d-none');
      }
    } catch (error) {
      errorOccurred = true;
      console.error('Error loading posts:', error);
      loadMoreBtn.textContent = 'Error - Click to Retry';
      loadMoreBtn.disabled = false;
    } finally {
      if (!errorOccurred && hasMore) {
        loadMoreBtn.disabled = false;
        loadMoreBtn.textContent = 'Load More Posts';
      }
    }
  }

  if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', loadMorePosts);
  }