// Javascript for the gradio app

document.addEventListener("DOMContentLoaded", function() {
  console.log("[Gradio Script] DOM fully loaded");
  
  setupCompletionButtonObserver();
  
  setupCopyPrevention();
});

function setupCompletionButtonObserver() {
  const observer = new MutationObserver((mutations) => {
    // Look for the next-scenario-btn that has the study-completed-btn class
    const completionBtn = document.querySelector("#next-scenario-btn.study-completed-btn");
    
    if (completionBtn) {
      console.log("[Gradio Script] Study completion button detected");
      
      completionBtn.setAttribute("data-study-completed", "true");
      
      completionBtn.classList.add("btn-primary");
      
      const completionEvent = new CustomEvent("studyCompleted", {
        detail: { message: "All scenarios have been completed" }
      });
      
      window.dispatchEvent(completionEvent);
      console.log("[Gradio Script] Dispatched studyCompleted event");
    }
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["class"]
  });
  
  console.log("[Gradio Script] Completion button observer set up");
}

function setupCopyPrevention() {
  function applyPreventionToElement(element) {
    if (!element) return;
    
    console.log("[Gradio Script] Applying copy prevention to:", element);
    
    element.addEventListener('contextmenu', function(e) {
      e.preventDefault();
      console.log("[Gradio Script] Prevented context menu on task element");
      return false;
    });
    
    element.addEventListener('mousedown', function(e) {
      if (e.detail > 1) {
        e.preventDefault();
        console.log("[Gradio Script] Prevented selection via double-click");
      }
    });
    
    element.setAttribute('data-copy-protected', 'true');
  }
  
  const taskElement = document.getElementById('scenario-task');
  if (taskElement && !taskElement.hasAttribute('data-copy-protected')) {
    applyPreventionToElement(taskElement);
  }
  
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.addedNodes && mutation.addedNodes.length > 0) {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1 && node.id === 'scenario-task' && !node.hasAttribute('data-copy-protected')) {
            applyPreventionToElement(node);
          }
          
          if (node.nodeType === 1 && node.querySelector) {
            const taskElements = node.querySelectorAll('#scenario-task, .scenario-task, .header-task');
            taskElements.forEach(element => {
              if (!element.hasAttribute('data-copy-protected')) {
                applyPreventionToElement(element);
              }
            });
          }
        });
      }
    });
  });
  
  observer.observe(document, {
    childList: true,
    subtree: true
  });
  
  document.addEventListener('copy', function(e) {
    const selection = window.getSelection();
    if (selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      const taskElement = document.getElementById('scenario-task');
      const taskElementClasses = document.querySelectorAll('.scenario-task, .header-task');
      
      function isOrContainsTaskElement(element) {
        if (!element) return false;
        if (element.id === 'scenario-task') return true;
        if (element.classList && 
            (element.classList.contains('scenario-task') || 
             element.classList.contains('header-task'))) return true;
        return false;
      }
      
      const commonAncestor = range.commonAncestorContainer;
      
      if (commonAncestor.nodeType === 1 && isOrContainsTaskElement(commonAncestor)) {
        e.preventDefault();
        console.log("[Gradio Script] Prevented copy from task element");
        return false;
      }
      
      if (commonAncestor.nodeType === 3 && commonAncestor.parentNode && 
          isOrContainsTaskElement(commonAncestor.parentNode)) {
        e.preventDefault();
        console.log("[Gradio Script] Prevented copy from task text");
        return false;
      }
    }
  });
  
  console.log("[Gradio Script] Copy prevention setup completed");
}