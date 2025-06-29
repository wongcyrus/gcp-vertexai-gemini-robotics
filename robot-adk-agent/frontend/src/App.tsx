/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useRef, useState, useEffect } from "react";
import "./App.scss";
import { LiveAPIProvider } from "./contexts/LiveAPIContext";
import SidePanel from "./components/side-panel/SidePanel";
import ControlTray from "./components/control-tray/ControlTray";
import cn from "classnames";

// Get host from URL query parameters or use default
const getHostFromQuery = (): string => {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('host') || "ws://localhost:8000";
};

// Get user ID from URL query parameters or use default
const getUserIdFromQuery = (): string => {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('userId') || "cloud_student";
};

const defaultHost = getHostFromQuery();
const defaultUserId = getUserIdFromQuery();

function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [serverUrl, setServerUrl] = useState<string>(defaultHost);
  const [runId] = useState<string>(crypto.randomUUID());
  const [userId, setUserId] = useState<string>(defaultUserId);

  // Update server URL and user ID if query parameters change
  useEffect(() => {
    const handleUrlChange = () => {
      const newHost = getHostFromQuery();
      const newUri = `ws://${newHost}/`;
      const newUserId = getUserIdFromQuery();
      setServerUrl(newUri);
      setUserId(newUserId);
    };

    // Listen for popstate events (back/forward navigation)
    window.addEventListener('popstate', handleUrlChange);
    
    return () => {
      window.removeEventListener('popstate', handleUrlChange);
    };
  }, []);

  return (
    <div className="App">
      <LiveAPIProvider url={serverUrl} userId={userId} runId={runId}>
        <div className="streaming-console">
          <SidePanel />
          <main>
            <div className="main-app-area">
              <video
                className={cn("stream", {
                  hidden: !videoRef.current || !videoStream,
                })}
                ref={videoRef}
                autoPlay
                playsInline
              />
            </div>
            <ControlTray
              videoRef={videoRef}
              supportsVideo={true}
              onVideoStreamChange={setVideoStream}
            >
            </ControlTray>
            <div className="url-setup" style={{position: 'absolute', top: 0, left: 0, right: 0, pointerEvents: 'auto', zIndex: 1000, padding: '2px', marginBottom: '2px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255, 255, 255, 0.9)'}}>
                <div>
                <img
                  src="https://hkiit.edu.hk/site/templates/images/HKIIT_Logo_bilingual.png"
                  alt="HKIIT Logo"
                  style={{ height: '40px', marginRight: '16px', verticalAlign: 'middle' }}
                />
                <h1 style={{ margin: '0 16px 0 0', fontSize: '24px', fontWeight: 600, display: 'inline-block', verticalAlign: 'middle' }}>
                  雲端系統及數據中心管理高級文憑
                </h1>
                <label htmlFor="server-url">Server URL:</label>
                <input
                  id="server-url"
                  type="text"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  placeholder="Enter server URL"
                  style={{
                  cursor: 'text',
                  padding: '4px',
                  margin: '0 4px', 
                  borderRadius: '2px',
                  border: '1px solid #ccc',
                  fontSize: '14px',
                  fontFamily: 'system-ui, -apple-system, sans-serif',
                  width: '200px'
                  }}
                />
                <label htmlFor="user-id">User ID:</label>
                <input
                  id="user-id"
                  type="text"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="Enter user ID"
                  style={{
                  cursor: 'text',
                  padding: '4px',
                  margin: '0 4px', 
                  borderRadius: '2px',
                  border: '1px solid #ccc',
                  fontSize: '14px',
                  fontFamily: 'system-ui, -apple-system, sans-serif',
                  width: '100px'
                  }}
                />
                </div>
            </div>

          </main>
        </div>
      </LiveAPIProvider>
    </div>
  );
}

export default App;
