---
layout: default
---

# Notes & Essays

A minimalist index of thoughts, technical write-ups, and ideas.

---

### All Posts

<ul>
{% for post in site.posts %}
  <li>
    {{ post.date | date: "%Y-%m-%d" }} &mdash; <a href="{{ post.url }}">{{ post.title }}</a>
  </li>
{% endfor %}
</ul>