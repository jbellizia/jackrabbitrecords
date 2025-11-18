import React, { useEffect, useState } from "react";
import YouTube from "react-youtube";

// --- Utility: Extract clean 11-char video ID ---
function extractYouTubeId(url) {
    if (!url) return null;

    const regex =
        /(?:youtube\.com\/(?:[^/]+\/.+\/|(?:v|embed|shorts)\/|.*[?&]v=)|youtu\.be\/)([^"&?/ ]{11})/i;

    const match = url.match(regex);
    return match ? match[1] : null;
}

// --- Utility: Check if that ID is embeddable ---
async function checkEmbeddable(videoId) {
    if (!videoId) return false;
    try {
        const res = await fetch(`/api/check-youtube-embed?id=${videoId}`);
        const data = await res.json();
        return data.embeddable;
    } catch (err) {
        console.error("Error checking embed ability:", err);
        return false;
    }
}

export default function YoutubeVideo({ url }) {
    const [videoId, setVideoId] = useState(null);
    const [canEmbed, setCanEmbed] = useState(null); 

    useEffect(() => {
        const id = extractYouTubeId(url);
        setVideoId(id);
        if (id) {
            checkEmbeddable(id).then(setCanEmbed);
        } else {
            setCanEmbed(false);
        }
    }, [url]);

    const options = {
        width: "100%",
        height: "100%",
        playerVars: {
            autoplay: 0,
            controls: 1,
        },
    };

    if (!canEmbed || !videoId) {
        return (
            <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="yt-fallback"
            >
                Watch on YouTube
            </a>
        );
    }

    return (
        <YouTube
            videoId={videoId}
            opts={options}
            onReady={(event) => event.target.pauseVideo()}
            id="video"
        />
    );
}
