from pdf_processor import PdfProcessor, print_pdf_summary
import asyncio

async def main():
    pdf_processor = PdfProcessor("https://antilogicalism.com/wp-content/uploads/2017/07/atlas-shrugged.pdf")
    # Note: This might return a huge full_text in the results
    results = await pdf_processor.process_url(pdf_processor.url, 'Who is John Galt?')
    print_pdf_summary(results)

if __name__ == "__main__":
    asyncio.run(main())
