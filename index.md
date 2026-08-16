---
layout: default
---

{% for post in site.posts %}
  <div class="post-entry">
    <div class="post-date">{{ post.date | date: "%b %d, %Y" }}</div>
    <a class="post-title" href="{{ post.url }}">{{ post.title }}</a>
    <p class="post-snippet">{{ post.description }}</p>
  </div>
{% endfor %}