import { useState, useEffect } from 'react';

export function OptionalVideo() {
  const [showVideo, setShowVideo] = useState(false);

  useEffect(() => {
    const checkVideo = async () => {
      try {
        const response = await fetch('/demo.mp4', { method: 'HEAD' });
        if (response.ok) {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.startsWith('video/')) {
            setShowVideo(true);
          }
        }
      } catch (error) {
        // Video not available, show nothing
      }
    };

    checkVideo();
  }, []);

  if (!showVideo) {
    return null;
  }

  return (
    <section className="bg-background py-20">
      <div className="max-w-5xl mx-auto px-6">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-text-primary mb-8">
          See ScanTract in action
        </h2>
        <div className="rounded-xl overflow-hidden shadow-lg">
          <video
            controls
            muted
            playsInline
            className="w-full"
            src="/demo.mp4"
          >
            Your browser does not support the video tag.
          </video>
        </div>
      </div>
    </section>
  );
}
