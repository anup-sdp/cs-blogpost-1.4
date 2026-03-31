// Error message extraction from API responses
export function getErrorMessage(error) {
  if (typeof error.detail === "string") {
    return error.detail;
  } else if (Array.isArray(error.detail)) {
    return error.detail.map((err) => err.msg).join(". ");
  }
  return "An error occurred. Please try again.";
}

// Show a Bootstrap modal by ID
export function showModal(modalId) {
  const modal = bootstrap.Modal.getOrCreateInstance(
    document.getElementById(modalId),
  );
  modal.show();
  return modal;
}

// Hide a Bootstrap modal by ID
export function hideModal(modalId) {
  const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
  if (modal) modal.hide();
}
// bootstrap.Modal is assumed to be globally available, Modal API is available globally since Bootstrap attaches to window.bootstrap

// XSS prevention for dynamic content insertion
export function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  // ^ The browser automatically stores it in a text node; no HTML parsing occurs. Any characters that would normally start tags (<, >, &, ", ', etc.) remain literal.
  return div.innerHTML;
  // ^ Reading innerHTML forces the browser to serialize the content of the text node back into an HTML string. During serialization, the browser performs its built-in escaping:
  // & → &amp; < → &lt; > → &gt; " → &quot; (in some contexts); ' → &#39; (in some contexts)
}
/*
# python, Escape it when rendering
import html
user_input= "<script>alert(1)</script>"
safe = html.escape(user_input)
# & -> &amp;, < -> &lt;, etc.
print(safe) # &lt;script&gt;alert(1)&lt;/script&gt;
*/
/*
This function is a a client-side JavaScript utility, it's a common, clever "hack" used to sanitize text by converting special characters into their HTML-encoded equivalents. 
It prevents Cross-Site Scripting (XSS) when you need to inject user-provided text into a webpage.
The function turns "active" code characters into "passive" text entities:
Input (text)                Output (Return Value)
-------------------------- --------------------------------------
Hello World                 Hello World (No change)
<script>alert(1)</script>   &lt;script&gt;alert(1)&lt;/script&gt;
<b>Bold</b>                 &lt;b&gt;Bold&lt;/b&gt;
1 < 2 & 3 > 0               1 &lt; 2 &amp; 3 &gt; 0
*/
// better: validate+sanitize on server, but this is a good extra layer of defense for client-side rendering of user input. use both client-side and server-side
// or, Escape on output, not on input. ? -----
// {{ post.content }} Jinja2 auto-escapes by default → safe. // use bleach library, bleach.clean(post.content) to sanitize on server-side

// Date formatting to match server's strftime("%B %d, %Y")
export function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "2-digit",
  });
}
/*
"2026-01-01" -> "January 01, 2026"
"2026-03-17T15:00:00" -> "March 17, 2026"
*/