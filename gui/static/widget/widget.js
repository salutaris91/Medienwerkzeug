(function () {
  var script = document.currentScript || (function () {
    var scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  var baseUrl = script.src.replace('/static/widget/widget.js', '');
  var politicianId = script.getAttribute('data-politician') || '';
  var topic = script.getAttribute('data-topic') || '';
  var width = script.getAttribute('data-width') || '520';
  var height = script.getAttribute('data-height') || '600';

  var params = new URLSearchParams();
  if (politicianId) params.set('politician', politicianId);
  if (topic) params.set('topic', topic);

  var iframeSrc = baseUrl + '/widget?' + params.toString();

  var iframe = document.createElement('iframe');
  iframe.src = iframeSrc;
  iframe.width = width;
  iframe.height = height;
  iframe.style.border = 'none';
  iframe.style.borderRadius = '12px';
  iframe.style.display = 'block';
  iframe.allow = 'same-origin';
  iframe.title = 'Kritik senden';

  script.parentNode.insertBefore(iframe, script.nextSibling);
})();
