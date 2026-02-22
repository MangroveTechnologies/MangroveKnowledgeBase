/**
 * Knowledge Base Document Server - Search UX
 */

(function() {
    'use strict';

    // =============================================================================
    // Keyboard Shortcuts
    // =============================================================================

    document.addEventListener('keydown', function(e) {
        // Focus search with '/' key
        if (e.key === '/' && !isInputFocused()) {
            e.preventDefault();
            const searchInput = document.getElementById('global-search');
            if (searchInput) {
                searchInput.focus();
            }
        }

        // Escape to blur search
        if (e.key === 'Escape') {
            const searchInput = document.getElementById('global-search');
            if (searchInput && document.activeElement === searchInput) {
                searchInput.blur();
            }
        }
    });

    function isInputFocused() {
        const activeElement = document.activeElement;
        return activeElement && (
            activeElement.tagName === 'INPUT' ||
            activeElement.tagName === 'TEXTAREA' ||
            activeElement.isContentEditable
        );
    }

    // =============================================================================
    // Search Debouncing (for instant search)
    // =============================================================================

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // =============================================================================
    // Instant Search (optional - for search page)
    // =============================================================================

    const searchFormLarge = document.querySelector('.search-form-large');
    if (searchFormLarge) {
        const searchInput = searchFormLarge.querySelector('.search-input-large');
        
        // Add instant search preview (optional enhancement)
        // Uncomment to enable:
        /*
        const debouncedSearch = debounce(async function(query) {
            if (query.length < 2) return;
            
            try {
                const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=5`);
                const data = await response.json();
                displaySearchPreview(data);
            } catch (error) {
                console.error('Search error:', error);
            }
        }, 300);

        searchInput.addEventListener('input', function(e) {
            debouncedSearch(e.target.value);
        });
        */
    }

    // =============================================================================
    // Tag Filter Form Submission
    // =============================================================================

    const tagFilterCheckboxes = document.querySelectorAll('.tag-filter input');
    tagFilterCheckboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            // Get all checked tags
            const checkedTags = Array.from(tagFilterCheckboxes)
                .filter(cb => cb.checked)
                .map(cb => cb.value);
            
            // Update URL with selected tags
            const form = checkbox.closest('form');
            if (form) {
                // Create hidden input for tags if needed
                let tagsInput = form.querySelector('input[name="tags"]');
                if (!tagsInput) {
                    tagsInput = document.createElement('input');
                    tagsInput.type = 'hidden';
                    tagsInput.name = 'tags';
                    form.appendChild(tagsInput);
                }
                tagsInput.value = checkedTags.join(',');
            }
        });
    });

    // =============================================================================
    // Table of Contents Highlighting
    // =============================================================================

    const tocItems = document.querySelectorAll('.toc-item');
    if (tocItems.length > 0) {
        const headings = document.querySelectorAll('h2[id], h3[id]');
        
        function updateActiveToc() {
            let currentId = '';
            
            headings.forEach(function(heading) {
                const rect = heading.getBoundingClientRect();
                if (rect.top <= 120) {
                    currentId = heading.id;
                }
            });
            
            tocItems.forEach(function(item) {
                item.classList.remove('active');
                if (item.getAttribute('data-anchor') === currentId || 
                    item.getAttribute('href') === '#' + currentId) {
                    item.classList.add('active');
                }
            });
        }
        
        window.addEventListener('scroll', debounce(updateActiveToc, 50));
        updateActiveToc();
    }

    // =============================================================================
    // Smooth Scroll for Anchor Links
    // =============================================================================

    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href.length > 1) {
                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                    
                    // Update URL without scrolling
                    history.pushState(null, null, href);
                }
            }
        });
    });

    // =============================================================================
    // Code Block Copy Button
    // =============================================================================

    document.querySelectorAll('.document-content pre').forEach(function(pre) {
        // Create copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-code-btn';
        copyBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
        copyBtn.title = 'Copy code';
        
        // Position the button
        pre.style.position = 'relative';
        copyBtn.style.cssText = 'position: absolute; top: 0.5rem; right: 0.5rem; background: var(--bg-elevated); border: 1px solid var(--border-color); border-radius: 4px; padding: 0.375rem; cursor: pointer; opacity: 0; transition: opacity 0.2s;';
        
        pre.appendChild(copyBtn);
        
        // Show/hide on hover
        pre.addEventListener('mouseenter', function() {
            copyBtn.style.opacity = '1';
        });
        pre.addEventListener('mouseleave', function() {
            copyBtn.style.opacity = '0';
        });
        
        // Copy functionality
        copyBtn.addEventListener('click', async function() {
            const code = pre.querySelector('code');
            const text = code ? code.textContent : pre.textContent;
            
            try {
                await navigator.clipboard.writeText(text);
                copyBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>';
                setTimeout(function() {
                    copyBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
                }, 2000);
            } catch (err) {
                console.error('Failed to copy:', err);
            }
        });
    });

    // =============================================================================
    // Mobile Sidebar Toggle
    // =============================================================================

    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
        
        // Close sidebar on outside click
        document.addEventListener('click', function(e) {
            if (sidebar.classList.contains('open') && 
                !sidebar.contains(e.target) && 
                !menuToggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }

    // =============================================================================
    // Search Highlight Preservation on Page Load
    // =============================================================================

    // Highlight search terms in content when coming from search results
    function highlightSearchTerms() {
        const urlParams = new URLSearchParams(window.location.search);
        const highlight = urlParams.get('highlight');
        
        if (highlight) {
            const terms = highlight.split(',').map(t => t.trim()).filter(t => t);
            const content = document.querySelector('.document-content');
            
            if (content && terms.length > 0) {
                terms.forEach(function(term) {
                    highlightTerm(content, term);
                });
            }
        }
    }

    function highlightTerm(element, term) {
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        const nodesToProcess = [];
        let node;
        
        while (node = walker.nextNode()) {
            if (node.nodeValue.toLowerCase().includes(term.toLowerCase())) {
                nodesToProcess.push(node);
            }
        }
        
        nodesToProcess.forEach(function(textNode) {
            const regex = new RegExp('(' + escapeRegex(term) + ')', 'gi');
            const parts = textNode.nodeValue.split(regex);
            
            if (parts.length > 1) {
                const fragment = document.createDocumentFragment();
                parts.forEach(function(part) {
                    if (part.toLowerCase() === term.toLowerCase()) {
                        const mark = document.createElement('mark');
                        mark.textContent = part;
                        fragment.appendChild(mark);
                    } else {
                        fragment.appendChild(document.createTextNode(part));
                    }
                });
                textNode.parentNode.replaceChild(fragment, textNode);
            }
        });
    }

    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    highlightSearchTerms();

    // =============================================================================
    // Related Trading Signals Section Enhancement
    // =============================================================================

    function enhanceSignalsSections() {
        const content = document.querySelector('.document-content');
        if (!content) return;

        // Find all H4 headings
        const h4Elements = content.querySelectorAll('h4');
        
        h4Elements.forEach(function(h4) {
            // Check if this is a "Related Trading Signals" heading
            if (h4.textContent.trim() === 'Related Trading Signals') {
                // Create wrapper div
                const wrapper = document.createElement('div');
                wrapper.className = 'signals-section';
                
                // Insert wrapper before the h4
                h4.parentNode.insertBefore(wrapper, h4);
                
                // Move h4 into wrapper
                wrapper.appendChild(h4);
                
                // Collect all content until next h4 or hr
                let nextSibling = wrapper.nextSibling;
                while (nextSibling) {
                    const nodeName = nextSibling.nodeName.toLowerCase();
                    
                    // Stop at next heading or horizontal rule
                    if (nodeName === 'h2' || nodeName === 'h3' || nodeName === 'h4' || nodeName === 'hr') {
                        break;
                    }
                    
                    // Move element into wrapper
                    const elementToMove = nextSibling;
                    nextSibling = nextSibling.nextSibling;
                    wrapper.appendChild(elementToMove);
                    
                    // If this is a paragraph with a bold element as first child (signal name)
                    if (nodeName === 'p') {
                        const firstChild = elementToMove.firstChild;
                        if (firstChild && firstChild.nodeName === 'STRONG') {
                            firstChild.className = 'signal-name';
                        }
                    }
                }
            }
        });
    }

    // Run enhancement after page load
    enhanceSignalsSections();

})();

