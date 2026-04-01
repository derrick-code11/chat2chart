export default function UserBubble({ message }) {
  return (
    <div className="flex justify-end mb-3.5">
      <div className="max-w-[68%] bg-brand-dark text-brand-bg px-3.5 py-2.5 rounded-[6px] rounded-br-[2px] text-sm leading-[1.55] whitespace-pre-wrap wrap-break-word">
        {message.content}
      </div>
    </div>
  );
}
