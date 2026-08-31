/**
 * blog_editor.js — TechLife CMS Blog Editor
 * CKEditor 5 Classic Build (CDN) with custom SimpleUploadAdapter
 * compatible with the existing django-ckeditor-uploader endpoint.
 *
 * Instance tracking: window.__ck5Instances = { 'post_description': editorInstance }
 * Destroy-on-reinit guard: destroys existing instance before creating a new one.
 */

(function () {
    'use strict';

    // ── CKEditor 5 CDN ────────────────────────────────────────────────────────
    var CK5_CDN_URL = 'https://cdn.ckeditor.com/ckeditor5/39.0.1/super-build/ckeditor.js';
    var CK5_SCRIPT_ID = 'ckeditor5-cdn';

    // Global instance registry (keyed by textarea id)
    window.__ck5Instances = window.__ck5Instances || {};

    // ── Upload URL helper ─────────────────────────────────────────────────────
    function getUploadUrl(form) {
        if (!form) return '';
        return form.getAttribute('data-ckeditor-upload-url') || '';
    }

    // ── Script loader ─────────────────────────────────────────────────────────
    function loadScript(url, id, onLoad) {
        if (!url) {
            if (typeof onLoad === 'function') onLoad(false);
            return;
        }
        if (id) {
            var existing = document.getElementById(id);
            if (existing) {
                if (window.ClassicEditor) {
                    if (typeof onLoad === 'function') onLoad(true);
                    return;
                }
                existing.addEventListener('load', function () {
                    if (typeof onLoad === 'function') onLoad(true);
                }, { once: true });
                return;
            }
        }
        var script = document.createElement('script');
        if (id) script.id = id;
        script.src = url;
        script.async = true;
        script.onload = function () {
            if (typeof onLoad === 'function') onLoad(true);
        };
        script.onerror = function () {
            console.warn('[blog_editor] Failed to load CKEditor 5 from CDN:', url);
            if (typeof onLoad === 'function') onLoad(false);
        };
        document.head.appendChild(script);
    }

    function ensureCK5(callback) {
        if (window.ClassicEditor) {
            if (typeof callback === 'function') callback(true);
            return;
        }
        if (window.CKEditor5 && window.CKEditor5.ClassicEditor) {
            window.ClassicEditor = window.CKEditor5.ClassicEditor;
            if (typeof callback === 'function') callback(true);
            return;
        }
        loadScript(CK5_CDN_URL, CK5_SCRIPT_ID, function (ok) {
            if (window.CKEditor5 && window.CKEditor5.ClassicEditor) {
                window.ClassicEditor = window.CKEditor5.ClassicEditor;
            }
            if (typeof callback === 'function') callback(ok);
        });
    }

    // ── Custom Upload Adapter ─────────────────────────────────────────────────
    // Wraps the existing django-ckeditor-uploader endpoint (/ckeditor/upload/).
    // CK4 endpoint returns: { url: "...", filename: "..." }
    // CK5 expects resolve({ default: url }) on success.
    function DjangoCKUploadAdapter(loader, uploadUrl) {
        this.loader = loader;
        this.uploadUrl = uploadUrl;
    }

    DjangoCKUploadAdapter.prototype.upload = function () {
        var loader = this.loader;
        var uploadUrl = this.uploadUrl;

        return loader.file.then(function (file) {
            return new Promise(function (resolve, reject) {
                // Get CSRF token from cookie
                var csrfToken = '';
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var c = cookies[i].trim();
                    if (c.startsWith('csrftoken=')) {
                        csrfToken = c.substring('csrftoken='.length);
                        break;
                    }
                }

                var formData = new FormData();
                formData.append('upload', file);

                var xhr = new XMLHttpRequest();
                xhr.open('POST', uploadUrl + '?type=Images', true);
                xhr.setRequestHeader('X-CSRFToken', csrfToken);

                xhr.upload.onprogress = function (e) {
                    if (e.lengthComputable) {
                        loader.uploadTotal = e.total;
                        loader.uploaded = e.loaded;
                    }
                };

                xhr.onload = function () {
                    if (xhr.status < 200 || xhr.status >= 300) {
                        return reject('Upload failed: HTTP ' + xhr.status);
                    }
                    try {
                        var data = JSON.parse(xhr.responseText);
                        // django-ckeditor-uploader returns { url: "...", filename: "..." }
                        // CKEditor 5 SimpleUploadAdapter expects { default: url }
                        var url = data.url || data.default;
                        if (url) {
                            resolve({ default: url });
                        } else {
                            reject('Upload response did not contain an image URL.');
                        }
                    } catch (e) {
                        reject('Could not parse upload response.');
                    }
                };

                xhr.onerror = function () {
                    reject('Upload failed due to a network error.');
                };

                xhr.send(formData);
            });
        });
    };

    DjangoCKUploadAdapter.prototype.abort = function () {
        if (this.xhr) this.xhr.abort();
    };

    function uploadAdapterPlugin(uploadUrl) {
        return function (editor) {
            editor.plugins.get('FileRepository').createUploadAdapter = function (loader) {
                return new DjangoCKUploadAdapter(loader, uploadUrl);
            };
        };
    }

    // ── Editor Config ─────────────────────────────────────────────────────────
    function buildEditorConfig(form) {
        var uploadUrl = getUploadUrl(form);
        var config = {
            toolbar: {
                items: [
                    'heading', '|',
                    'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', 'highlight', '|',
                    'bold', 'italic', 'underline', 'strikethrough', 'code', 'subscript', 'superscript', 'removeFormat', '|',
                    'alignment', '|',
                    'bulletedList', 'numberedList', 'todoList', '|',
                    'outdent', 'indent', '|',
                    'link', 'imageUpload', 'blockQuote', 'insertTable', 'mediaEmbed', 'codeBlock', 'htmlEmbed', '|',
                    'undo', 'redo', '|',
                    'findAndReplace', 'sourceEditing'
                ],
                shouldNotGroupWhenFull: true
            },
            heading: {
                options: [
                    { model: 'paragraph', title: 'Paragraph', class: 'ck-heading_paragraph' },
                    { model: 'heading1', view: 'h1', title: 'Heading 1', class: 'ck-heading_heading1' },
                    { model: 'heading2', view: 'h2', title: 'Heading 2', class: 'ck-heading_heading2' },
                    { model: 'heading3', view: 'h3', title: 'Heading 3', class: 'ck-heading_heading3' },
                    { model: 'heading4', view: 'h4', title: 'Heading 4', class: 'ck-heading_heading4' },
                ]
            },
            table: {
                contentToolbar: ['tableColumn', 'tableRow', 'mergeTableCells', 'tableCellProperties', 'tableProperties']
            },
            image: {
                toolbar: [
                    'imageStyle:inline', 'imageStyle:block', 'imageStyle:side',
                    '|', 'toggleImageCaption', 'imageTextAlternative'
                ]
            },
            htmlSupport: {
                allow: [
                    { name: /./, attributes: true, classes: true, styles: true }
                ]
            },
        };

        // Wire up upload adapter if URL is provided
        if (uploadUrl) {
            config.extraPlugins = [uploadAdapterPlugin(uploadUrl)];
        }

        return config;
    }

    // ── Init CKEditor 5 ───────────────────────────────────────────────────────
    function initCkeditor() {
        var textarea = document.getElementById('post_description');
        if (!textarea) return;

        var form = document.getElementById('create-blog-form');
        if (form && form.getAttribute('data-editor') === 'tiptap') {
            return; // Skip CKEditor initialization
        }

        ensureCK5(function (ok) {
            if (!window.ClassicEditor) {
                console.warn('[blog_editor] ClassicEditor not available.');
                return;
            }

            // Destroy existing instance if present (reinit guard)
            if (window.__ck5Instances['post_description']) {
                window.__ck5Instances['post_description'].destroy()
                    .then(function () {
                        _createEditor(textarea, form);
                    })
                    .catch(function (err) {
                        console.warn('[blog_editor] Destroy error:', err);
                        _createEditor(textarea, form);
                    });
            } else {
                _createEditor(textarea, form);
            }
        });
    }

    function _createEditor(textarea, form) {
        textarea.removeAttribute('required');
        var config = buildEditorConfig(form);

        ClassicEditor.create(textarea, config)
            .then(function (editor) {
                window.__ck5Instances['post_description'] = editor;

                // Sync data back to textarea on every change (for form validation)
                editor.model.document.on('change:data', function () {
                    var data = editor.getData();
                    textarea.value = data;
                    var errEl = document.getElementById('desc-error');
                    if (errEl && data.trim()) {
                        errEl.classList.add('hidden');
                    }
                });
            })
            .catch(function (err) {
                console.error('[blog_editor] CKEditor 5 init error:', err);
            });
    }

    // ── Form Validation ───────────────────────────────────────────────────────
    function bindFormValidation() {
        var form = document.getElementById('create-blog-form');
        if (!form || form.dataset.editorBound === 'true') return;
        form.dataset.editorBound = 'true';

        form.addEventListener('submit', function (e) {
            // Sync CK5 data to textarea before validation
            var editor = window.__ck5Instances['post_description'];
            if (editor) {
                var data = editor.getData();
                var desc = document.getElementById('post_description');
                if (desc) desc.value = data;
            }

            var desc = document.getElementById('post_description');
            var errEl = document.getElementById('desc-error');
            var content = (desc ? desc.value : '').trim();

            if (!content) {
                e.preventDefault();
                if (errEl) errEl.classList.remove('hidden');
                return false;
            }
            if (errEl) errEl.classList.add('hidden');

            var btn = document.getElementById('create-submit-btn');
            var text = document.getElementById('submit-text');
            if (btn && text) {
                btn.disabled = true;
                var isEdit = form.dataset.isEdit === 'true';
                text.textContent = isEdit ? 'Saving...' : 'Publishing...';
            }

            return true;
        });
    }

    // ── Tag System ────────────────────────────────────────────────────────────
    function initTagSystem() {
        var tagBox = document.getElementById('tag-box');
        if (!tagBox || tagBox.dataset.tagsBound === 'true') return;
        tagBox.dataset.tagsBound = 'true';

        var selectedTags = {};
        var preselectedTags = [];
        var selectedTagsEl = document.getElementById('selected-tags-data');
        if (selectedTagsEl && selectedTagsEl.textContent) {
            try {
                preselectedTags = JSON.parse(selectedTagsEl.textContent);
            } catch (e) {
                preselectedTags = [];
            }
        }

        var input = document.getElementById('tag-input');
        var chipsEl = document.getElementById('tag-chips');
        var suggestions = document.getElementById('tag-suggestions');

        if (!input || !chipsEl || !suggestions) return;

        function escapeHtml(str) {
            return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function renderChips() {
            chipsEl.innerHTML = '';
            Object.entries(selectedTags).forEach(function (entry) {
                var key = entry[0];
                var tag = entry[1];
                var chip = document.createElement('span');
                chip.className = 'inline-flex items-center gap-1 pl-2.5 pr-1.5 py-1 rounded-full text-[11px] font-semibold bg-[#1e3a6e] text-white';
                chip.innerHTML =
                    '<span>' + escapeHtml(tag.label) + '</span>' +
                    '<button type="button" onclick="removeTagByKey(\'' + key.replace(/'/g, "\\'") + '\')" ' +
                    'class="w-4 h-4 rounded-full bg-white/20 hover:bg-white/40 flex items-center justify-center flex-shrink-0 transition-colors" ' +
                    'aria-label="Remove tag">' +
                    '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
                    '</button>';
                chipsEl.appendChild(chip);
            });
        }

        function syncCheckboxes() {
            var hiddenInput = document.getElementById('post_tags_hidden');
            if (hiddenInput) {
                var tagNames = Object.values(selectedTags).map(function(t) { return t.label; });
                hiddenInput.value = tagNames.join(',');
            }
            
            // Keep existing behavior just in case
            var allCbs = document.querySelectorAll('#tag-hidden-checkboxes input[type="checkbox"]');
            allCbs.forEach(function (cb) { cb.checked = false; });
            Object.values(selectedTags).forEach(function (tag) {
                if (tag.id) {
                    var cb = document.getElementById('tag-cb-' + tag.id);
                    if (cb) cb.checked = true;
                }
            });
        }

        function removeTag(key) {
            var tag = selectedTags[key];
            if (!tag) return;
            if (tag.isExisting) {
                var btn = document.querySelector('.tag-suggestion-btn[data-tag-id="' + tag.id + '"]');
                if (btn) {
                    btn.classList.remove('bg-[#1e3a6e]', 'text-white', 'border-[#1e3a6e]');
                    btn.classList.add('bg-gray-50', 'text-gray-700', 'border-gray-200');
                    var icon = btn.querySelector('svg');
                    if (icon) icon.style.display = '';
                }
            }
            delete selectedTags[key];
            renderChips();
            syncCheckboxes();
        }

        function addCustomTag(label) {
            var key = 'custom_' + label.toLowerCase();
            if (selectedTags[key]) return;
            var btns = document.querySelectorAll('.tag-suggestion-btn');
            var matched = null;
            btns.forEach(function (btn) {
                if (btn.dataset.tagLabel.toLowerCase() === label.toLowerCase()) {
                    matched = btn;
                }
            });
            if (matched) {
                window.addTagFromSuggestion(matched);
                return;
            }
            selectedTags[key] = { id: '', label: label, isExisting: false };
            renderChips();
        }

        window.removeTagByKey = function (key) { removeTag(key); };

        window.addTagFromSuggestion = function (btn) {
            var id = btn.dataset.tagId;
            var label = btn.dataset.tagLabel;
            var key = 'id_' + id;
            if (selectedTags[key]) return;
            selectedTags[key] = { id: id, label: label, isExisting: true };
            renderChips();
            syncCheckboxes();
            btn.classList.add('bg-[#1e3a6e]', 'text-white', 'border-[#1e3a6e]');
            btn.classList.remove('bg-gray-50', 'text-gray-700', 'border-gray-200');
            var icon = btn.querySelector('svg');
            if (icon) icon.style.display = 'none';
            input.focus();
        };

        input.addEventListener('focus', function () { suggestions.classList.remove('hidden'); });

        document.addEventListener('click', function (e) {
            var box = document.getElementById('tag-box');
            if (box && !box.contains(e.target) && !suggestions.contains(e.target)) {
                suggestions.classList.add('hidden');
            }
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                var val = input.value.trim().replace(/,+$/, '');
                if (val) addCustomTag(val);
                input.value = '';
            }
            if (e.key === 'Backspace' && input.value === '') {
                var keys = Object.keys(selectedTags);
                if (keys.length > 0) removeTag(keys[keys.length - 1]);
            }
        });

        input.addEventListener('input', function () {
            var q = input.value.toLowerCase();
            var btns = document.querySelectorAll('.tag-suggestion-btn');
            btns.forEach(function (btn) {
                var label = btn.dataset.tagLabel.toLowerCase();
                btn.style.display = label.includes(q) ? '' : 'none';
            });
            suggestions.classList.remove('hidden');
        });

        if (preselectedTags.length) {
            preselectedTags.forEach(function (tag) {
                var btn = document.querySelector('.tag-suggestion-btn[data-tag-id="' + tag.id + '"]');
                if (btn) {
                    window.addTagFromSuggestion(btn);
                    return;
                }
                if (tag.label) {
                    var key = 'custom_' + tag.label.toLowerCase();
                    if (!selectedTags[key]) {
                        selectedTags[key] = { id: '', label: tag.label, isExisting: false };
                    }
                }
            });
            renderChips();
            syncCheckboxes();
        }
    }

    // ── Image Preview ─────────────────────────────────────────────────────────
    function initImagePreview() {
        var imgInput = document.getElementById('featured_image');
        var imgPreview = document.getElementById('image-preview');
        if (!imgInput || !imgPreview || imgInput.dataset.previewBound === 'true') return;
        imgInput.dataset.previewBound = 'true';

        imgInput.addEventListener('change', function () {
            var file = this.files && this.files[0];
            if (!file) return;
            var reader = new FileReader();
            reader.onload = function (e) {
                imgPreview.src = e.target.result;
                imgPreview.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        });
    }

    // ── Boot ──────────────────────────────────────────────────────────────────
    function initBlogEditor() {
        initCkeditor();
        bindFormValidation();
        initTagSystem();
        initImagePreview();
    }

    document.addEventListener('DOMContentLoaded', initBlogEditor);
    document.addEventListener('htmx:afterSwap', initBlogEditor);
    document.addEventListener('htmx:historyRestore', initBlogEditor);
})();
