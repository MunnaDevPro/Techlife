function printBlogContent() {
    const contentToPrint = document.getElementById('blog-content-to-print').innerHTML;
    const originalContent = document.body.innerHTML;
    document.body.innerHTML = contentToPrint;
    window.print();
    document.body.innerHTML = originalContent;
}