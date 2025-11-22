import { useEffect } from "react";

export default function Splash({ onEnter }) {
    
    useEffect(() => {
        document.body.style.overflow = "hidden"; // disable scroll
        return () => {
            document.body.style.overflow = "auto";
        };
    }, []);

    return (
        <div className="w-screen h-screen flex items-center justify-center"        >
            <div className="w-[60vw] md:w-[30vw] lg:w-[20vw] transform hover:scale-110 active:scale-95 transition duration-300 cursor-pointer" onClick={onEnter}>
                <img
                    src="/src/assets/loading-logo.png"
                    alt="THE JRR LOGO"
                    className="w-full spin-slow cursor-pointer object-contain cursor-pointer"
                />
            </div>
        </div>
    );
}