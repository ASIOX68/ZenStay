import React, { useRef, useState } from "react";
import axios from "axios";
import { Upload, Image as ImageIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { useLang } from "../contexts/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ImageUpload({ value, onChange }) {
  const { t } = useLang();
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  const pick = () => inputRef.current?.click();

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) {
      toast.error("Max 8 MB");
      return;
    }
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await axios.post(`${API}/admin/upload`, fd, {
        withCredentials: true,
        headers: { "Content-Type": "multipart/form-data" },
      });
      onChange(r.data.url);
      toast.success("OK");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Upload erreur");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="w-20 h-20 rounded-xl bg-muted border border-border flex items-center justify-center overflow-hidden shrink-0">
          {value ? (
            <img src={value} alt="" className="w-full h-full object-cover" />
          ) : (
            <ImageIcon className="w-5 h-5 text-muted-foreground" />
          )}
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={pick}
          disabled={uploading}
          className="rounded-xl"
          data-testid="image-upload-btn"
        >
          <Upload className="w-4 h-4 mr-2" />
          {uploading ? t.admin_upload.uploading : t.admin_upload.choose}
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          className="hidden"
          onChange={upload}
          data-testid="image-upload-input"
        />
      </div>
      <Input
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t.admin_upload.or_url}
        data-testid="image-url-input"
      />
    </div>
  );
}
