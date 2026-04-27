(function () {
    'use strict';

    var CKEDITOR_CDN_FALLBACK = 'https://cdn.ckeditor.com/4.25.1-lts/full/ckeditor.js';
    var CKEDITOR_SCRIPT_ID = 'ckeditor-cdn';

    function getCkeditorUrls(form) {
        if (!form) {
            return {};
        }
        return {
            uploadUrl: form.getAttribute('data-ckeditor-upload-url') || '',
            browseUrl: form.getAttribute('data-ckeditor-browse-url') || '',
        };
    }

    function loadScript(url, id, onLoad, fallbackUrl) {
        if (!url) {
            if (typeof onLoad === 'function') onLoad(false);
            return;
        }

        if (id) {
            var existing = document.getElementById(id);
            if (existing) {
                if (window.CKEDITOR) {
                    if (typeof onLoad === 'function') onLoad(true);
                    return;
                }
                existing.addEventListener('load', function () {
                    if (typeof onLoad === 'function') onLoad(true);
                }, { once: true });
                existing.addEventListener('error', function () {
                    existing.remove();
                    if (fallbackUrl && fallbackUrl !== url) {
                        loadScript(fallbackUrl, id, onLoad);
                        return;
                    }
                    if (typeof onLoad === 'function') onLoad(false);
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
            if (id) {
                var failed = document.getElementById(id);
                if (failed) failed.remove();
            }
            if (fallbackUrl && fallbackUrl !== url) {
                loadScript(fallbackUrl, id, onLoad);
                return;
            }
            if (typeof onLoad === 'function') onLoad(false);
        };
        document.head.appendChild(script);
    }

    function ensureCkeditor(callback) {
        if (window.CKEDITOR) {
            if (typeof callback === 'function') callback();
            return;
        }

        var cdnUrl = window.CKEDITOR_CDN_URL || CKEDITOR_CDN_FALLBACK;
        var localUrl = window.CKEDITOR_LOCAL_URL || '';

        loadScript(cdnUrl, CKEDITOR_SCRIPT_ID, function () {
            if (window.CKEDITOR) {
                if (typeof callback === 'function') callback();
                return;
            }
            if (localUrl) {
                loadScript(localUrl, CKEDITOR_SCRIPT_ID, function () {
                    if (typeof callback === 'function') callback();
                });
            }
        }, localUrl || null);
    }

    function buildEditorConfig(form) {
        var urls = getCkeditorUrls(form);
        var uploadUrl = urls.uploadUrl;
        var browseUrl = urls.browseUrl;

        return {
            toolbar: [
                { name: 'clipboard', items: ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo'] },
                { name: 'editing', items: ['Find', 'Replace', '-', 'SelectAll'] },
                { name: 'insert', items: ['Image', 'Table', 'HorizontalRule', 'SpecialChar', 'PageBreak', 'Smiley', 'Iframe'] },
                '/',
                { name: 'basicstyles', items: ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', 'RemoveFormat'] },
                { name: 'paragraph', items: ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote', 'CreateDiv', '-', 'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'] },
                { name: 'links', items: ['Link', 'Unlink', 'Anchor'] },
                { name: 'styles', items: ['Styles', 'Format', 'Font', 'FontSize'] },
                { name: 'colors', items: ['TextColor', 'BGColor'] },
                { name: 'tools', items: ['Maximize', 'ShowBlocks', 'Preview', 'Print', 'Source'] },
            ],
            height: 520,
            filebrowserUploadUrl: uploadUrl,
            filebrowserBrowseUrl: browseUrl,
            filebrowserImageUploadUrl: uploadUrl ? (uploadUrl + '?type=Images') : '',
            filebrowserImageBrowseUrl: browseUrl ? (browseUrl + '?type=Images') : '',
            allowedContent: true,
            extraAllowedContent: 'script[*](*); iframe[*](*); *(*)',
            entities: false,
            versionCheck: false,
            removePlugins: 'exportpdf',
            contentsCss: [
                'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap',
                'body { font-family: Inter, sans-serif; font-size: 14px; line-height: 1.8; color: #1c1c1e; padding: 12px 16px; background: #fff; }' +
                'p { margin: 0 0 1em 0; }' +
                'h1,h2,h3,h4,h5,h6 { font-weight: 700; line-height: 1.3; margin: 1.2em 0 0.5em; }' +
                'a { color: #1e3a6e; }' +
                'blockquote { border-left: 3px solid #1e3a6e; margin: 1em 0; padding: 0.5em 1em; color: #555; background: #f9fafb; }' +
                'img { max-width: 100%; height: auto; border-radius: 6px; }'
            ],
            bodyClass: 'ckeditor-content'
        };
    }

    function initCkeditor() {
        var textarea = document.getElementById('post_description');
        if (!textarea) {
            return;
        }

        var form = document.getElementById('create-blog-form');

        ensureCkeditor(function () {
            if (!window.CKEDITOR) {
                return;
            }

            if (CKEDITOR.instances.post_description) {
                CKEDITOR.instances.post_description.destroy(true);
            }

            CKEDITOR.config.versionCheck = false;
            CKEDITOR.replace('post_description', buildEditorConfig(form));
        });
    }

    function bindFormValidation() {
        var form = document.getElementById('create-blog-form');
        if (!form || form.dataset.editorBound === 'true') {
            return;
        }

        form.dataset.editorBound = 'true';

        form.addEventListener('submit', function (e) {
            if (typeof CKEDITOR !== 'undefined' && CKEDITOR.instances.post_description) {
                CKEDITOR.instances.post_description.updateElement();
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

    function initTagSystem() {
        var tagBox = document.getElementById('tag-box');
        if (!tagBox || tagBox.dataset.tagsBound === 'true') {
            return;
        }

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

        if (!input || !chipsEl || !suggestions) {
            return;
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
            var allCbs = document.querySelectorAll('#tag-hidden-checkboxes input[type="checkbox"]');
            allCbs.forEach(function (cb) { cb.checked = false; });
            Object.values(selectedTags).forEach(function (tag) {
                if (tag.id) {
                    var cb = document.getElementById('tag-cb-' + tag.id);
                    if (cb) cb.checked = true;
                }
            });
        }

        function escapeHtml(str) {
            return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
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

        window.removeTagByKey = function (key) {
            removeTag(key);
        };

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

        input.addEventListener('focus', function () {
            suggestions.classList.remove('hidden');
        });

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

    function initImagePreview() {
        var imgInput = document.getElementById('featured_image');
        var imgPreview = document.getElementById('image-preview');
        if (!imgInput || !imgPreview || imgInput.dataset.previewBound === 'true') {
            return;
        }

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

    function initBlogEditor() {
        initCkeditor();
        bindFormValidation();
        initTagSystem();
        initImagePreview();
    }

    document.addEventListener('DOMContentLoaded', initBlogEditor);
    document.body.addEventListener('htmx:afterSwap', initBlogEditor);
    document.body.addEventListener('htmx:historyRestore', initBlogEditor);
})();
