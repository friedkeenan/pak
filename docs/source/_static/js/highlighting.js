/*
    Remove highlighting from all syntax-highlighted
    elements that are children of a link element.

    There might be a more direct way of doing this
    through sphinx, but I'm not sure how to otherwise
    detect that a literal reference actually gets
    a link attached or not.
*/
document.querySelectorAll("a > .highlight").forEach(highlighted => {
    highlighted.classList.remove("highlight");
})
