import streamlit as st
import pandas as pd
import re
from googleapiclient.discovery import build
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import plotly.express as px
import urllib.request
import os

# ---------------------------------------------------------
# 1. 페이지 기본 설정 및 귀여운 커스텀 CSS (파스텔 톤)
# ---------------------------------------------------------
st.set_page_config(
    page_title="🎬 몽글몽글 유튜브 댓글 탐정단",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
    <style>
    /* 전체 배경 및 폰트 설정 */
    .main {
        background-color: #FAFAFF;
    }
    
    /* 제목 스타일 */
    .main-title {
        color: #FF6B81;
        font-size: 2.3rem;
        font-weight: bold;
        text-align: center;
        padding: 10px;
        background-color: #FFEAEF;
        border-radius: 20px;
        margin-bottom: 25px;
        border: 2px dashed #FF8E9E;
    }

    /* 카드형 컨테이너 */
    .custom-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 18px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #EAEAEA;
    }
    
    /* 서브 타이틀 */
    .sub-title {
        color: #4A69BD;
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 한글 폰트 설정 (Streamlit Cloud 자동 다운로드)
# ---------------------------------------------------------
@st.cache_resource
def get_korean_font():
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        urllib.request.urlretrieve(url, font_path)
    return font_path

font_path = get_korean_font()

# ---------------------------------------------------------
# 3. 유튜브 API 데이터 가져오기 함수
# ---------------------------------------------------------
def extract_video_id(url):
    """유튜브 URL에서 Video ID 추출"""
    regex = r"(?:v=|\/([0-9A-Za-z_-]{11}).*|s\/|embed\/|youtu.be\/|\/v\/|\/e\/|watch\?v=|&v=)([^#&?]*)"
    match = re.search(regex, url)
    if match:
        return match.group(1) if len(match.group(1)) == 11 else match.group(2)
    return None

def fetch_comments(api_key, video_id, max_comments=100):
    """유튜브 댓글 및 수집 시각, 좋아요 수 수집"""
    youtube = build("youtube", "v3", developerKey=api_key)
    comments = []
    
    next_page_token = None
    fetched_count = 0

    while fetched_count < max_comments:
        limit = min(100, max_comments - fetched_count)
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=limit,
            pageToken=next_page_token,
            textFormat="plainText"
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "author": snippet["authorDisplayName"],
                "text": snippet["textDisplay"],
                "published_at": pd.to_datetime(snippet["publishedAt"]),
                "like_count": snippet["likeCount"]
            })
            fetched_count += 1
            if fetched_count >= max_comments:
                break

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return pd.DataFrame(comments)

# ---------------------------------------------------------
# 4. 사이드바 - 설정 창
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 분석 설정하기")
    api_key = st.text_input("🔑 YouTube API Key를 입력하세요", type="password")
    max_comments = st.slider("💬 가져올 댓글 개수", min_value=10, max_value=500, value=100, step=10)
    
    st.markdown("---")
    st.info("💡 **안내**: 구글 클라우드 콘솔에서 발급받은 API 키를 입력해 주세요!")

# ---------------------------------------------------------
# 5. 메인 화면 구성
# ---------------------------------------------------------
st.markdown("<div class='main-title'>🎬 몽글몽글 유튜브 댓글 탐정단 🔍</div>", unsafe_allow_html=True)

video_url = st.text_input("📌 분석하고 싶은 유튜브 영상 링크(URL)를 입력하세요", placeholder="https://www.youtube.com/watch?v=...")

if video_url:
    video_id = extract_video_id(video_url)
    
    if not video_id:
        st.error("❌ 올바른 유튜브 링크가 아니에요! 다시 확인해 주세요.")
    elif not api_key:
        st.warning("👈 왼쪽 사이드바에 YouTube API Key를 입력해 주세요!")
    else:
        # 영상 화면 보이기
        st.video(f"https://www.youtube.com/watch?v={video_id}")
        
        # 댓글 불러오기 버튼
        if st.button("🚀 댓글 분석 시작하기!", use_container_width=True):
            with st.spinner("🕵️‍♂️ 댓글을 열심히 모으고 있어요... 잠시만 기다려 주세요!"):
                try:
                    df = fetch_comments(api_key, video_id, max_comments)
                    
                    if df.empty:
                        st.warning("💬 댓글이 없거나 가져올 수 없는 영상이에요.")
                    else:
                        st.success(f"🎉 총 {len(df)}개의 댓글을 성공적으로 분석했어요!")
                        
                        # ---------------------------------------------------------
                        # 시각화 1: 시간대별 댓글 작성 추이
                        # ---------------------------------------------------------
                        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                        st.markdown("<div class='sub-title'>📈 1. 시간대별 댓글은 언제 많이 달렸을까?</div>", unsafe_allow_html=True)
                        
                        df_time = df.set_index("published_at").resample("D").size().reset_index(name="count")
                        fig_time = px.line(
                            df_time, 
                            x="published_at", 
                            y="count",
                            labels={"published_at": "날짜", "count": "댓글 수"},
                            markers=True,
                            color_discrete_sequence=["#FF6B81"]
                        )
                        fig_time.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(245,246,250,1)",
                            font=dict(family="NanumGothic", size=13)
                        )
                        st.plotly_chart(fig_time, use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # ---------------------------------------------------------
                        # 시각화 2: 댓글 반응도 (좋아요 상위 댓글 & 반응 통계)
                        # ---------------------------------------------------------
                        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                        st.markdown("<div class='sub-title'>❤️ 2. 친구들이 가장 좋아한 인기 댓글 (Top 3)</div>", unsafe_allow_html=True)
                        
                        top_liked = df.sort_values(by="like_count", ascending=False).head(3)
                        
                        for idx, row in top_liked.iterrows():
                            st.info(f"👍 **좋아요 {row['like_count']}개** | **{row['author']}**: {row['text']}")
                            
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # ---------------------------------------------------------
                        # 시각화 3: 한글 워드클라우드
                        # ---------------------------------------------------------
                        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                        st.markdown("<div class='sub-title'>☁️ 3. 어떤 단어가 가장 많이 나왔을까? (한글 워드클라우드)</div>", unsafe_allow_html=True)
                        
                        # 한글 단어만 추출 (2글자 이상)
                        all_text = " ".join(df["text"].tolist())
                        words = re.findall(r'[가-힣]{2,}', all_text)
                        
                        # 불용어(제외할 무의미한 단어) 처리
                        stopwords = set(["너무", "진짜", "완전", "그냥", "오늘", "영상", "유튜브", "ㅋㅋ", "ㅎㅎ"])
                        words = [w for w in words if w not in stopwords]
                        
                        cleaned_text = " ".join(words)
                        
                        if cleaned_text.strip():
                            wc = WordCloud(
                                font_path=font_path,
                                background_color="white",
                                width=800,
                                height=400,
                                colormap="Pastel1", # 귀여운 파스텔 칼라맵
                                max_words=80
                            ).generate(cleaned_text)
                            
                            fig_wc, ax = plt.subplots(figsize=(10, 5))
                            ax.imshow(wc, interpolation="bilinear")
                            ax.axis("off")
                            st.pyplot(fig_wc)
                        else:
                            st.write("워드클라우드를 만들 한글 단어가 부족해요!")
                            
                        st.markdown("</div>", unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"오류가 발생했어요. API 키나 영상 링크를 확인해 보세요!\n\n상세 오류: {e}")

else:
    # 초기 안내 카드
    st.markdown("""
        <div class='custom-card' style='text-align: center; padding: 40px;'>
            <h3>👋 반가워요! 탐정단 친구들!</h3>
            <p>궁금한 유튜브 영상 URL과 API Key를 입력하면<br>댓글에 담긴 다양한 비밀을 시각화 그래프로 찾아줄게요!</p>
        </div>
    """, unsafe_allow_html=True)
