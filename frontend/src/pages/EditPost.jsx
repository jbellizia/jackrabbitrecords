import { useParams, useNavigate, useOutletContext } from "react-router-dom";
import { useState, useEffect } from "react";

export default function EditPost() {
    const { postId } = useParams();
    const navigate = useNavigate();
    const { setGlobalLoading } = useOutletContext();
    const [post, setPost] = useState(null);
    const [title, setTitle] = useState("");
    const [blurb, setBlurb] = useState("");
    const [writeup, setWriteup] = useState("");
    const [media_type, set_media_type] = useState("none");
    const [media_file, set_media_file] = useState(null);
    const [media_href, set_media_href] = useState("");
    const [is_visible, set_is_visible] = useState("");
    useEffect(() => {
        fetch(`/api/post/${postId}`)
            .then((res) => res.json())
            .then((data) => {
                setPost(data);
                setTitle(data.title || "");
                setBlurb(data.blurb || "");
                setWriteup(data.writeup || "");
                set_media_type(data.media_type || "none");
                set_media_href(data.media_href || "");
                set_is_visible(Boolean(data.is_visible));
                set_media_file(null);
            })
    }, [postId]);

    const handleMediaTypeChange = (e) => {
        const new_type = e.target.value;
        const externalTypes = ["video", "link"];
        if (externalTypes.includes(media_type) && externalTypes.includes(new_type)) {
            set_media_type(new_type);
            return;
        }
        if (media_type !== "none" && media_type !== new_type) {
            const confirmed = window.confirm(
                "Changing the media type will remove the current media from this post. Are you sure?"
            );
            if (!confirmed) {
                e.target.value = media_type;
                return;
            }
            set_media_file(null);
            set_media_href("");
        }
        set_media_type(new_type);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setGlobalLoading(true);

        const formData = new FormData();
        formData.append("title", title);
        formData.append("blurb", blurb);
        formData.append("writeup", writeup);
        formData.append("media_type", media_type);
        formData.append("is_visible", is_visible)

        if (media_type === "image" && media_file) {
            formData.append("image", media_file);
        } else if (media_type === "audio" && media_file) {
            formData.append("audio", media_file);
        } else if (media_href) {
            formData.append("media_href", media_href);
        }

        try {
            const res = await fetch(`/api/posts/${postId}`, {
                method: "POST",
                body: formData,
                credentials: "include",
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || "Unknown error");
            }

            // Give the overlay a short grace period for smoother UX
            await new Promise((r) => setTimeout(r, 300));

            navigate(-1);
        } catch (err) {
            console.error("Update failed:", err);
            alert("Failed to update post: " + err.message);
        } finally {
            setGlobalLoading(false);
        }
    };


    if (!post) return <p>Post not found</p>;

    return (
        <div className="w-[60vw] ml-[20vw] mr-[20vw] flex flex-col gap-5 cursor-default mt-[2.5vw]">
            <h2 className="text-3xl self-center">Edit Post</h2>
            <form onSubmit={handleSubmit} className="flex-col flex gap-5">
                <input
                    type="text"
                    placeholder="Title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="border p-2"
                />
                <input
                    type="text"
                    placeholder="Blurb"
                    value={blurb}
                    onChange={(e) => setBlurb(e.target.value)}
                    className="border p-2"
                />
                <textarea
                    placeholder="Writeup"
                    value={writeup}
                    onChange={(e) => setWriteup(e.target.value)}
                    className="border p-2"
                />
                <select value={media_type} onChange={handleMediaTypeChange} className="border p-2">
                    <option value="none">None</option>
                    <option value="image">Image</option>
                    <option value="video">Youtube Video</option>
                    <option value="audio">Audio</option>
                    <option value="link">Link</option>
                </select>

                {media_type === "image" ? (
                    <div className="flex flex-col gap-3">
                        {media_href && !media_file && (
                            <img src={`/api${post.media_href}`} alt="Current" className="w-[50%] self-center"/>
                        )}
                        <input
                            type="file"
                            accept="image/*"
                            onChange={(e) => set_media_file(e.target.files[0])}
                            className="cursor-pointer p-2 hover:bg-gray-100 rounded-md border"
                        />
                    </div>
                ) : media_type === "video" || media_type === "link" ? (
                    <input
                        type="text"
                        placeholder="Media URL"
                        value={media_href ?? ""}
                        onChange={(e) => set_media_href(e.target.value)}
                        className="border block p-2"
                    />
                ) : media_type === "audio" ? (
                    <div>
                        {media_href && !media_file && (
                            <audio controls src={`/api${post.media_href}`} />
                        )}
                        <input
                            type="file"
                            accept="audio/*"
                            onChange={(e) => set_media_file(e.target.files[0])}
                            className="cursor-pointer p-2 hover:bg-gray-200 rounded-md border"
                        />
                    </div>
                ) : null}
                <div>
                    <label >
                        Make post visible
                    </label>
                    <input type="hidden" name="is_visible" value="0" />
                    <input
                        type="checkbox"
                        name="is_visible"
                        id="is_visible"
                        value="1"
                        checked={!!is_visible}
                        onChange={(e) => set_is_visible(e.target.checked)}
                    />
                </div>
                <button type="submit" className="border cursor-pointer p-2 bg-gray-100 hover:bg-gray-200 rounded-md">
                    Update Post
                </button>
            </form>
        </div>
    );
}
