/**
 * Knowledge Base Sidebar - Expand/Collapse Functionality
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'kb_sidebar_collapsed_docs';

    // Load collapsed state from localStorage
    function loadCollapsedState() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            return stored ? JSON.parse(stored) : [];
        } catch (e) {
            console.error('Failed to load sidebar state:', e);
            return [];
        }
    }

    // Save collapsed state to localStorage
    function saveCollapsedState(collapsedDocs) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(collapsedDocs));
        } catch (e) {
            console.error('Failed to save sidebar state:', e);
        }
    }

    // Initialize sidebar state
    function initializeSidebar() {
        const collapsedDocs = loadCollapsedState();
        
        // Apply collapsed state to tree items
        collapsedDocs.forEach(function(docSlug) {
            const treeItem = document.querySelector('.tree-item[data-doc="' + docSlug + '"]');
            if (treeItem) {
                treeItem.classList.add('collapsed');
            }
        });

        // Add toggle button click handlers
        const toggleButtons = document.querySelectorAll('.tree-toggle');
        toggleButtons.forEach(function(button) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                toggleSection(this);
            });
        });
    }

    // Toggle a section's expanded/collapsed state
    function toggleSection(button) {
        const docSlug = button.getAttribute('data-doc');
        const treeItem = button.closest('.tree-item');
        
        if (!treeItem) return;

        const isCollapsed = treeItem.classList.contains('collapsed');
        
        if (isCollapsed) {
            // Expand
            treeItem.classList.remove('collapsed');
            removeFromCollapsed(docSlug);
        } else {
            // Collapse
            treeItem.classList.add('collapsed');
            addToCollapsed(docSlug);
        }
    }

    // Add document to collapsed list
    function addToCollapsed(docSlug) {
        const collapsedDocs = loadCollapsedState();
        if (!collapsedDocs.includes(docSlug)) {
            collapsedDocs.push(docSlug);
            saveCollapsedState(collapsedDocs);
        }
    }

    // Remove document from collapsed list
    function removeFromCollapsed(docSlug) {
        let collapsedDocs = loadCollapsedState();
        collapsedDocs = collapsedDocs.filter(function(slug) {
            return slug !== docSlug;
        });
        saveCollapsedState(collapsedDocs);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeSidebar);
    } else {
        initializeSidebar();
    }

})();
