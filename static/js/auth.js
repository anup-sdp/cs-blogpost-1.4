// client-side auth helper

let currentUser = null;
let fetchPromise = null;

export async function getCurrentUser() {
  if (currentUser) {
    return currentUser;
  }

  // Return in-progress fetch to prevent duplicate API calls
  if (fetchPromise) {
    return fetchPromise;
  }

  const token = localStorage.getItem("access_token");
  if (!token) {
    return null;
  }

  fetchPromise = (async () => {
    try {
      const response = await fetch("/api/users/me", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        currentUser = await response.json();
        return currentUser;
      }

      localStorage.removeItem("access_token");
      return null;
    } catch (error) {
      console.error("Error fetching current user:", error);
      return null;
    } finally {
      fetchPromise = null;
    }
  })();

  return fetchPromise;
}

export function logout() {
  localStorage.removeItem("access_token");
  currentUser = null;
  window.location.href = "/";
}

export function getToken() {
  return localStorage.getItem("access_token");
}

export function setToken(token) {
  localStorage.setItem("access_token", token);
}

export function clearUserCache() {
  currentUser = null;
}

/*
summary: (by gpt-5 mini in gitgub)
Purpose: client-side auth helper for a single-page app.
Manages a cached current user object and the JWT access token stored in localStorage under the key "access_token".
Exports these functions:
-getCurrentUser(): Returns the cached user if available. If not, and a token exists, fetches the current user from the backend endpoint /api/users/me using Authorization: Bearer <token>. It deduplicates concurrent calls by storing an in-progress promise in fetchPromise so multiple callers share the same network request. On success it caches and returns the user; on failure it removes the token and returns null. It also logs fetch errors.
-logout(): Clears the token and cached user, then redirects the browser to "/".
-getToken(): Reads and returns the token from localStorage.
-setToken(token): Saves the token to localStorage.
-clearUserCache(): Clears only the cached currentUser (so the next getCurrentUser will refetch).
Behavior notes:
If the token is missing or the /api/users/me response is not OK, the token is removed to prevent future invalid requests.
fetchPromise prevents duplicate simultaneous fetches for the current user.
Suitable for SPA flows that need to get the authenticated user's info and manage login/logout state.
*/