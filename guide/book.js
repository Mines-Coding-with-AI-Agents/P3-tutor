/* Copy buttons on command blocks and on the words to say to a window. Works without it: the commands stay selectable text. */
(function () {
  function addCopy(block) {
    var head = block.querySelector(".cmd-head, .say-head");
    var pre = block.querySelector("pre.in, .say > pre");
    if (!head || !pre || head.querySelector(".copy")) return;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy";
    btn.textContent = "Copy";
    btn.addEventListener("click", function () {
      var text = pre.innerText.replace(/^\$ /gm, "");
      function done(label) { btn.textContent = label; setTimeout(function () { btn.textContent = "Copy"; }, 1500); }
      try {
        navigator.clipboard.writeText(text).then(function () { done("Copied"); }, function () { select(pre); done("Selected"); });
      } catch (e) { select(pre); done("Selected"); }
    });
    head.appendChild(btn);
  }
  function select(node) {
    try { var r = document.createRange(); r.selectNodeContents(node); var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); } catch (e) {}
  }
  document.querySelectorAll(".cmd, .say").forEach(addCopy);
  /* On a narrow screen the chapter list starts folded, so the chapter itself is the first thing you see. */
  if (window.matchMedia && window.matchMedia("(max-width: 979px)").matches) {
    document.querySelectorAll("details.toc-box").forEach(function (d) { d.removeAttribute("open"); });
  }
  /* On a wide screen the chapter list scrolls in its own column; start it with the current chapter in view. */
  function showCurrent() {
    var toc = document.querySelector(".toc");
    var current = document.querySelector(".toc-list a.current");
    if (!toc || !current || toc.scrollHeight <= toc.clientHeight) return;
    var top = current.getBoundingClientRect().top - toc.getBoundingClientRect().top + toc.scrollTop;
    toc.scrollTop = Math.max(0, top - toc.clientHeight / 2);
  }
  showCurrent();
  /* The web fonts can re-wrap the list after this runs, so place it again once they have loaded. */
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(showCurrent);
})();
