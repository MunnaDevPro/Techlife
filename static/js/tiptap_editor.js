// tiptap_editor.js - TechLife Dashboard Tiptap Editor integration
import { Editor } from 'https://esm.sh/@tiptap/core@2.1.13';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit@2.1.13';
import Underline from 'https://esm.sh/@tiptap/extension-underline@2.1.13';
import TextAlign from 'https://esm.sh/@tiptap/extension-text-align@2.1.13';
import Highlight from 'https://esm.sh/@tiptap/extension-highlight@2.1.13';
import TextStyle from 'https://esm.sh/@tiptap/extension-text-style@2.1.13';
import Color from 'https://esm.sh/@tiptap/extension-color@2.1.13';
import Image from 'https://esm.sh/@tiptap/extension-image@2.1.13';
import Link from 'https://esm.sh/@tiptap/extension-link@2.1.13';
import Table from 'https://esm.sh/@tiptap/extension-table@2.1.13';
import TableRow from 'https://esm.sh/@tiptap/extension-table-row@2.1.13';
import TableHeader from 'https://esm.sh/@tiptap/extension-table-header@2.1.13';
import TableCell from 'https://esm.sh/@tiptap/extension-table-cell@2.1.13';

document.addEventListener('DOMContentLoaded', () => {
    const textarea = document.getElementById('post_description');
    if (!textarea) return;

    const editorContainer = document.getElementById('tiptap-editor-container');
    if (!editorContainer) return;

    const form = document.getElementById('create-blog-form');
    if (!form) return;

    // Initialize Tiptap Editor
    const editor = new Editor({
        element: editorContainer,
        extensions: [
            StarterKit.configure({
                bulletList: {
                    HTMLAttributes: { class: 'list-disc pl-5 my-2' }
                },
                orderedList: {
                    HTMLAttributes: { class: 'list-decimal pl-5 my-2' }
                }
            }),
            Underline,
            TextAlign.configure({
                types: ['heading', 'paragraph'],
            }),
            Highlight.configure({
                HTMLAttributes: { class: 'bg-yellow-200 text-black px-1 rounded' },
                multicolor: true
            }),
            TextStyle,
            Color,
            Image.configure({
                HTMLAttributes: { class: 'max-w-full h-auto rounded border my-4 inline-block' }
            }),
            Link.configure({
                openOnClick: false,
                HTMLAttributes: { class: 'text-blue-600 underline hover:text-blue-800' }
            }),
            Table.configure({
                resizable: true,
                HTMLAttributes: { class: 'border-collapse w-full border border-gray-300 my-4' }
            }),
            TableRow,
            TableHeader.configure({
                HTMLAttributes: { class: 'border border-gray-300 bg-gray-50 px-3 py-2 font-bold text-left' }
            }),
            TableCell.configure({
                HTMLAttributes: { class: 'border border-gray-300 px-3 py-2 text-left' }
            })
        ],
        content: textarea.value,
        editorProps: {
            attributes: {
                class: 'prose-content min-h-[400px] max-h-[600px] overflow-y-auto outline-none p-4 w-full bg-white focus:ring-0 focus:border-transparent ProseMirror'
            }
        },
        onUpdate({ editor }) {
            // Sync content back to Django's native textarea
            textarea.value = editor.getHTML();
        }
    });

    // Save editor instance to window object for access/debugging
    window.tiptapEditor = editor;

    // --- Toolbar Handlers ---
    const bindCommand = (selector, action) => {
        const btn = document.querySelector(selector);
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                action();
                editor.chain().focus().run();
            });
        }
    };

    // Basic Formatting
    bindCommand('.tiptap-bold', () => editor.chain().toggleBold().run());
    bindCommand('.tiptap-italic', () => editor.chain().toggleItalic().run());
    bindCommand('.tiptap-underline', () => editor.chain().toggleUnderline().run());
    bindCommand('.tiptap-strike', () => editor.chain().toggleStrike().run());
    bindCommand('.tiptap-code', () => editor.chain().toggleCode().run());

    // Headings & Blockquote / Code block / HR
    const selectHeading = document.getElementById('tiptap-heading-select');
    if (selectHeading) {
        selectHeading.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val === 'p') {
                editor.chain().setParagraph().focus().run();
            } else if (['1', '2', '3', '4'].includes(val)) {
                editor.chain().toggleHeading({ level: parseInt(val) }).focus().run();
            }
        });
        
        // Update Heading Select dropdown value based on cursor position/active node
        editor.on('selectionUpdate', () => {
            if (editor.isActive('heading', { level: 1 })) selectHeading.value = '1';
            else if (editor.isActive('heading', { level: 2 })) selectHeading.value = '2';
            else if (editor.isActive('heading', { level: 3 })) selectHeading.value = '3';
            else if (editor.isActive('heading', { level: 4 })) selectHeading.value = '4';
            else selectHeading.value = 'p';
        });
    }

    bindCommand('.tiptap-blockquote', () => editor.chain().toggleBlockquote().run());
    bindCommand('.tiptap-codeblock', () => editor.chain().toggleCodeBlock().run());
    bindCommand('.tiptap-hr', () => editor.chain().setHorizontalRule().run());

    // Alignment
    bindCommand('.tiptap-align-left', () => editor.chain().setTextAlign('left').run());
    bindCommand('.tiptap-align-center', () => editor.chain().setTextAlign('center').run());
    bindCommand('.tiptap-align-right', () => editor.chain().setTextAlign('right').run());
    bindCommand('.tiptap-align-justify', () => editor.chain().setTextAlign('justify').run());

    // Lists
    bindCommand('.tiptap-bullet-list', () => editor.chain().toggleBulletList().run());
    bindCommand('.tiptap-ordered-list', () => editor.chain().toggleOrderedList().run());

    // Colors & Highlights
    const textColorInput = document.getElementById('tiptap-text-color');
    if (textColorInput) {
        textColorInput.addEventListener('input', (e) => {
            editor.chain().setColor(e.target.value).focus().run();
        });
    }
    const highlightColorInput = document.getElementById('tiptap-highlight-color');
    if (highlightColorInput) {
        highlightColorInput.addEventListener('input', (e) => {
            editor.chain().setHighlight({ color: e.target.value }).focus().run();
        });
    }

    // Insert Link
    bindCommand('.tiptap-link', () => {
        const previousUrl = editor.getAttributes('link').href;
        const url = window.prompt('Enter Link URL:', previousUrl || 'https://');
        if (url === null) return;
        if (url === '') {
            editor.chain().unsetLink().run();
        } else {
            editor.chain().setLink({ href: url }).run();
        }
    });

    // Image Upload / URL
    bindCommand('.tiptap-image', () => {
        const url = window.prompt('Enter Image URL:');
        if (url) {
            editor.chain().setImage({ src: url }).run();
        }
    });

    // Table Insertion
    bindCommand('.tiptap-table', () => {
        editor.chain().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
    });

    // History & Utilities
    bindCommand('.tiptap-undo', () => editor.chain().undo().run());
    bindCommand('.tiptap-redo', () => editor.chain().redo().run());
    bindCommand('.tiptap-clear', () => {
        editor.chain().clearContent().run();
        textarea.value = '';
    });

    // Keep active states of buttons updated in UI
    const updateActiveStates = () => {
        const activeClass = 'bg-gray-200';
        
        const toggleClass = (selector, isActive) => {
            const btn = document.querySelector(selector);
            if (btn) {
                if (isActive) btn.classList.add(activeClass);
                else btn.classList.remove(activeClass);
            }
        };

        toggleClass('.tiptap-bold', editor.isActive('bold'));
        toggleClass('.tiptap-italic', editor.isActive('italic'));
        toggleClass('.tiptap-underline', editor.isActive('underline'));
        toggleClass('.tiptap-strike', editor.isActive('strike'));
        toggleClass('.tiptap-code', editor.isActive('code'));
        toggleClass('.tiptap-blockquote', editor.isActive('blockquote'));
        toggleClass('.tiptap-codeblock', editor.isActive('codeBlock'));
        toggleClass('.tiptap-bullet-list', editor.isActive('bulletList'));
        toggleClass('.tiptap-ordered-list', editor.isActive('orderedList'));
    };

    editor.on('transaction', updateActiveStates);
});
