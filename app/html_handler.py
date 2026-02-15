from app.html_cleaner import HtmlCleaner

class HtmlHandler:
    @staticmethod
    def get_info(link):
        html_obj = HtmlCleaner(link)

        html = html_obj.connect()

        if html == False:
            return "UNABLE TO GET INFO"

        try:
            html = html_obj.clean_html(html)
        except Exception as e:
            print(e)
            return "UNABLE TO CLEAN HTML"

        try:
            html = html_obj.extract_sections(html)
        except Exception as e:
            print(e)
            return "UNABLE TO EXTRACT SECTIONS"

        try:
            html = html_obj.remove_repetitions(html)
        except Exception as e:
            print(e)
            return "UNABLE TO REMOVE REPETITIONS FROM SECTIONS"

        try:
            for sec in html:
                for con in sec["content"]:
                    con = html_obj.normalize_text(con)
        except Exception as e:
            print(e)
            return "UNABLE TO NORMALIZE TEXT"
        
        try:
            html = html_obj.flatten_contents(html)
        except Exception as e:
            print(e)
            return "UNABLE TO FLATTEN CONTENT"

        return html


# if __name__ == "__main__":
#     print(HtmlHandler.get_info("https://www.amazon.com/dp/B0F2G2N96F/ref=sspa_dk_detail_0?psc=1&pd_rd_i=B0F2G2N96F&pd_rd_w=pk27z&content-id=amzn1.sym.e1bd46f6-106d-4001-8a1f-c5226d6c67ac&pf_rd_p=e1bd46f6-106d-4001-8a1f-c5226d6c67ac&pf_rd_r=KHMJFVE3QZ545ATAMBHV&pd_rd_wg=NPlHN&pd_rd_r=b2c47a40-09de-418f-9442-087b51bff528&sp_csd=d2lkZ2V0TmFtZT1zcF9kZXRhaWxfdGhlbWF0aWM"))
        